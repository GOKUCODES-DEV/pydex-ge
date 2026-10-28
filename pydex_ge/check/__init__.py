"""Error, syntax, and project checking for PYDEX.

``pydex_ge.check`` is a small, dependency-free toolkit for finding problems in a
PYDEX project without running a game window.  It is **static** and **safe**: it
only parses and compiles source code, it never imports your modules, and it
never opens a window.

Quick start::

    from pydex_ge import check_project
    report = check_project(".")

    print(report)                      # human-readable report
    if report.ok:
        print("PYDEX check passed.")

Available entry points (all available as ``pydex_ge.<name>`` too):

* :func:`check_file`     -- one Python file, every check
* :func:`check_python`   -- syntax, imports, and undefined names
* :func:`check_assets`   -- asset paths, dynamic paths, duplicate assets
* :func:`check_pydex`    -- PYDEX API/configuration/scene mistakes
* :func:`check_all`      -- every check (same as :func:`check_project`)
* :func:`check_project`  -- a whole folder, every check (the default)
* :func:`format_error`   -- turn a raised exception into one clean line

CLI usage::

    python -m pydex_ge.check                 # check the current directory
    python -m pydex_ge.check path/to/project
    python -m pydex_ge.check --all .
    python -m pydex_ge.check --json .
    python -m pydex_ge.check --quiet

Each result has a stable error ``code`` (``SYNTAX001``, ``IMPORT001``,
``NAME001``, ``PYDEX001``/``002``, ``CONFIG001``, ``SCENE001``,
``ASSET001``-``003``, ``PROJECT001``), a ``category``
(``syntax``/``import``/``name``/``pydex_ge``/``configuration``/``scene``/
``asset``/``project``), a ``severity`` (``error``/``warning``/``info``),
and an exact ``file:line:column`` when the checker can point at one.

Limitations (by design):

* It cannot reliably detect every runtime error -- it is static.
* It never executes project code.
* Dynamic Python behaviour (metaclasses, monkey-patching, ``exec``...) may
  not be detectable statically.
"""

from __future__ import annotations

import ast
import os
import sys

from ..exceptions import ConfigurationError
from ._analysis import (
    check_asset_paths,
    check_imports,
    check_names,
    check_pydex_usage,
    check_read_failure,
    check_syntax,
)
from ._format import render_result
from ._models import (
    CATEGORY_ASSET,
    CATEGORY_CONFIGURATION,
    CATEGORY_IMPORT,
    CATEGORY_NAME,
    CATEGORY_PROJECT,
    CATEGORY_PYDEX,
    CATEGORY_SCENE,
    CATEGORY_SYNTAX,
    CheckReport,
    CheckResult,
)
from ._scan import iter_asset_files, iter_python_files

_PYDEX_ROOT = os.path.normcase(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# A stable, documented set of error codes for the checker.
ERROR_CODES = {
    "SYNTAX001": "Invalid Python syntax / indentation / encoding error.",
    "IMPORT001": "Import from 'pydex_ge' of a name that does not exist.",
    "NAME001": "A name is read but looks like it was never defined.",
    "PYDEX001": "Unknown PYDEX name (with a likely typo suggestion).",
    "PYDEX002": "Attribute used directly on a PYDEX class that is not a public member.",
    "CONFIG001": "A clearly-invalid PYDEX configuration value.",
    "SCENE001": "SceneManager.push() receiving a non-Scene literal.",
    "ASSET001": "A literal asset path does not exist.",
    "ASSET002": "An asset path is dynamic and cannot be verified statically.",
    "ASSET003": "Duplicate asset files with the same name (ambiguous load).",
    "PROJECT001": "A project file could not be read.",
}

# Which categories run per mode.  check_python / check_assets / check_pydex /
# check_all select a subset; check_project is the same as check_all.
_ALL_CATEGORIES = frozenset(
    [
        CATEGORY_SYNTAX,
        CATEGORY_IMPORT,
        CATEGORY_NAME,
        CATEGORY_PYDEX,
        CATEGORY_CONFIGURATION,
        CATEGORY_SCENE,
        CATEGORY_ASSET,
        CATEGORY_PROJECT,
    ]
)

_PYTHON_CATEGORIES = frozenset(
    [CATEGORY_SYNTAX, CATEGORY_IMPORT, CATEGORY_NAME, CATEGORY_PROJECT]
)
_ASSET_CATEGORIES = frozenset([CATEGORY_ASSET, CATEGORY_PROJECT])
_PYDEX_CATEGORIES = frozenset(
    [
        CATEGORY_PYDEX,
        CATEGORY_CONFIGURATION,
        CATEGORY_SCENE,
        CATEGORY_SYNTAX,
        CATEGORY_NAME,
        CATEGORY_PROJECT,
    ]
)


def _in_pydex(filename: str) -> bool:
    """True when ``filename`` lives inside the PYDEX package itself."""
    return os.path.normcase(filename).startswith(_PYDEX_ROOT)


def _caller_info() -> str:
    """Return ``file:line`` of the first caller outside the PYDEX package."""
    frame = sys._getframe(1)
    while frame is not None:
        filename = frame.f_code.co_filename
        if filename and not _in_pydex(filename):
            return f"{filename}:{frame.f_lineno}"
        frame = frame.f_back
    return "<unknown>:0"


def _validate_path_arg(path: object, funcname: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ConfigurationError(f"{funcname}() needs a file or directory path.")
    return path.strip()


def _analyze_source(path: str, source: str, project_root: str, categories) -> list[CheckResult]:
    """Run the category-appropriate analyzers over decoded ``source``."""
    results: list[CheckResult] = []

    tree = None
    if CATEGORY_SYNTAX in categories:
        results.extend(check_syntax(path, source))
        if results:  # a syntax error stops everything else (unparseable).
            return results
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            tree = None
            return results
    else:
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            tree = None
        if tree is None:
            return results

    if CATEGORY_IMPORT in categories:
        results.extend(check_imports(path, source, tree))
    if CATEGORY_NAME in categories:
        results.extend(check_names(path, source, tree))
    if CATEGORY_PYDEX in categories or CATEGORY_SCENE in categories:
        results.extend(check_pydex_usage(path, source, tree))
    if CATEGORY_ASSET in categories:
        results.extend(
            check_asset_paths(path, source, tree, project_root)
        )
    # A mode may run a broader analyzer (e.g. name checks to find PYDEX
    # typos); only keep results whose category belongs to the mode.
    return [r for r in results if r.category in categories]


def _read_source_bytes(path: str) -> tuple[bytes | None, str | None, BaseException | None]:
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        text = raw.decode("utf-8", errors="replace")
        return raw, text, None
    except OSError as exc:
        return None, None, exc


def _check_python_file(
    path: str, project_root: str, categories
) -> CheckReport:
    raw, text, err = _read_source_bytes(path)
    if err is not None:
        return CheckReport(check_read_failure(path, err), root=path)
    results = _analyze_source(path, text or "", project_root, categories)
    return CheckReport(results, root=path)


def _walk_dir_with_categories(
    root: str, categories, *, include_assets: bool
) -> CheckReport:
    report = CheckReport(root=root)
    for rel, full in iter_python_files(root):
        report.extend(_check_python_file(full, root, categories))
    if include_assets and CATEGORY_ASSET in categories:
        report.extend(_check_duplicate_assets(root))
    report.sort(key=_result_sort_key)
    return report


def _check_duplicate_assets(root: str) -> list[CheckResult]:
    """Warn (ASSET003) when two asset files share the same basename."""
    by_name: dict[str, list[str]] = {}
    for rel, full in iter_asset_files(root):
        base = os.path.basename(rel).lower()
        by_name.setdefault(base, []).append(rel)
    results: list[CheckResult] = []
    for base, rels in sorted(by_name.items()):
        if len(rels) < 2:
            continue
        results.append(
            CheckResult(
                root,
                None,
                None,
                f"Two files have the same name ({base!r}): "
                + ", ".join(rels),
                severity="warning",
                code="ASSET003",
                category=CATEGORY_ASSET,
            )
        )
    return results


def _result_sort_key(result: CheckResult):
    return (
        os.path.normcase(result.path),
        result.lineno if result.lineno is not None else -1,
        result.column if result.column is not None else -1,
    )


def _resolve_target(path: object, funcname: str) -> str:
    path = _validate_path_arg(path, funcname)
    full = os.path.abspath(path)
    if not os.path.exists(full):
        raise FileNotFoundError(full)
    return full


# -- public API ------------------------------------------------------------


def check_file(path: str) -> list[CheckResult]:
    """Check one Python file with every static check.

    Parameters
    ----------
    path:
        Path to a ``.py``/``.pyw`` file.

    Returns
    -------
    list[CheckResult]
        One entry per problem.  An empty list means the file is valid.

    Raises
    ------
    ConfigurationError
        When ``path`` is not a non-empty string.
    FileNotFoundError
        When ``path`` does not exist or is not a file.
    """
    full = _resolve_target(path, "check_file")
    if not os.path.isfile(full):
        raise FileNotFoundError(full)
    project_root = os.path.dirname(full)
    return list(_check_python_file(full, project_root, _ALL_CATEGORIES))


def check_python(path: str) -> CheckReport:
    """Check Python files for syntax, imports, and undefined names.

    Accepts a single ``.py`` file or a directory (scanned recursively).
    Returns a :class:`CheckReport`.
    """
    full = _resolve_target(path, "check_python")
    if os.path.isfile(full):
        return _check_python_file(full, os.path.dirname(full), _PYTHON_CATEGORIES)
    return _walk_dir_with_categories(full, _PYTHON_CATEGORIES, include_assets=False)


def check_assets(path: str) -> CheckReport:
    """Check asset references (missing/dynamic/duplicate) in a file or folder.

    Accepts a single ``.py`` file or a directory.  Returns a
    :class:`CheckReport`.
    """
    full = _resolve_target(path, "check_assets")
    if os.path.isfile(full):
        return _check_python_file(full, os.path.dirname(full), _ASSET_CATEGORIES)
    return _walk_dir_with_categories(full, _ASSET_CATEGORIES, include_assets=True)


def check_pydex(path: str) -> CheckReport:
    """Check PYDEX-specific API, configuration, and scene usage.

    Accepts a single ``.py`` file or a directory.  Returns a
    :class:`CheckReport`.
    """
    full = _resolve_target(path, "check_pydex")
    if os.path.isfile(full):
        return _check_python_file(full, os.path.dirname(full), _PYDEX_CATEGORIES)
    return _walk_dir_with_categories(full, _PYDEX_CATEGORIES, include_assets=False)


def check_all(path: str) -> CheckReport:
    """Run every check on a file or a whole folder.

    Accepts a single ``.py`` file or a directory.  Returns a
    :class:`CheckReport`.
    """
    full = _resolve_target(path, "check_all")
    if os.path.isfile(full):
        return _check_python_file(full, os.path.dirname(full), _ALL_CATEGORIES)
    return _walk_dir_with_categories(full, _ALL_CATEGORIES, include_assets=True)


def check_project(root: str | None = None) -> CheckReport:
    """Check every file under a folder (default: the current directory).

    Equivalent to :func:`check_all` over a directory.  Hidden directories and
    common vendor/cache folders are skipped, and a ``.pydexignore`` file next
    to the project root is honoured.

    Parameters
    ----------
    root:
        Directory to walk.  ``None`` uses the current working directory.

    Returns
    -------
    CheckReport
        Behaves like a list of :class:`CheckResult` (so older ``for``/``len``
        code keeps working) and adds ``.errors``, ``.warnings``,
        ``.infos``, and ``.ok``.

    Raises
    ------
    ConfigurationError
        When ``root`` is not a non-empty string.
    NotADirectoryError
        When ``root`` is not a directory.
    """
    if root is None:
        root = os.getcwd()
    if not isinstance(root, str) or not root.strip():
        raise ConfigurationError("check_project() needs a directory path.")
    fullpath = os.path.abspath(root)
    if not os.path.isdir(fullpath):
        raise NotADirectoryError(fullpath)
    return _walk_dir_with_categories(
        fullpath, _ALL_CATEGORIES, include_assets=True
    )


def format_error(exc: BaseException) -> str:
    """Format an exception as ``file:line: ErrorType: message``.

    For a :class:`SyntaxError` the column is included
    (``file:line:column``).  For any other exception the location is the
    first frame of the traceback that belongs to *your* code rather than
    the PYDEX package; a missing-asset error additionally prefers its
    ``requested_by`` location.  When no useful location exists,
    ``<unknown>`` is used.
    """
    if isinstance(exc, SyntaxError) and exc.filename and exc.lineno:
        location = f"{exc.filename}:{exc.lineno}"
        if exc.offset:
            location += f":{exc.offset}"
        return f"{location}: SyntaxError: {exc.msg}"

    requested_by = getattr(exc, "requested_by", None)
    if requested_by:
        return f"{requested_by}: {type(exc).__name__}: {exc}"

    frame = exc.__traceback__
    while frame is not None:
        filename = frame.tb_frame.f_code.co_filename
        if filename and not _in_pydex(filename):
            return (
                f"{filename}:{frame.tb_lineno}: {type(exc).__name__}: {exc}"
            )
        frame = frame.tb_next

    filename = getattr(exc, "filename", None)
    lineno = getattr(exc, "lineno", None)
    if filename and lineno:
        return f"{filename}:{lineno}: {type(exc).__name__}: {exc}"
    return f"<unknown>: {type(exc).__name__}: {exc}"


def format_result(result: CheckResult) -> str:
    """Render a single :class:`CheckResult` with source context."""
    return render_result(result)


__all__ = [
    "CheckReport",
    "CheckResult",
    "ERROR_CODES",
    "check_all",
    "check_assets",
    "check_file",
    "check_project",
    "check_pydex",
    "check_python",
    "format_error",
    "format_result",
]