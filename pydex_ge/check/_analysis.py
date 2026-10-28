"""Static analysis of a single Python file.

Each analyzer returns :class:`~pydex_ge.check._models.CheckResult` objects with
a stable error ``code``, a ``category``, and a ``severity``.  Everything is
static: we parse/compile source only and never execute or import user code.
"""

from __future__ import annotations

import ast
import builtins
import difflib
import os

from ._api import (
    known_api_members,
    submodule_member_names,
    submodule_names,
    top_level_names,
)
from ._models import (
    CATEGORY_ASSET,
    CATEGORY_CONFIGURATION,
    CATEGORY_IMPORT,
    CATEGORY_NAME,
    CATEGORY_PROJECT,
    CATEGORY_PYDEX,
    CATEGORY_SCENE,
    CATEGORY_SYNTAX,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    CheckResult,
)

_BUILTINS = set(dir(builtins))
_GLOBAL_NAMES = frozenset(
    (
        "__name__",
        "__file__",
        "__doc__",
        "__package__",
        "__spec__",
        "__loader__",
        "__builtins__",
        "__annotations__",
        "pydex_ge",
    )
)

# f-string / peephole artifacts that look like names but are not.
_SAFE_NAMES = frozenset(("self", "cls"))

# Asset-loading call shapes: (callee name, callee attribute) -> (path arg
# index, path keyword name).  Attribute keys use lowercased instance names
# too (``assets.image``, ``audio.load_sound``), so both ``Assets.image()``
# and ``assets.image()`` are recognised.  ``Sprite(path)`` is the only
# path-taking sprite constructor; there is no ``Sprite.from_file()`` and
# ``SpriteSheet`` takes an ``Image``, not a path.
_ASSET_CALLS = {
    ("Image", None): (0, "path"),
    ("Sprite", None): (0, "source"),
    ("Font", None): (0, "path"),
    ("Sound", None): (0, "path"),
    ("Music", None): (0, "path"),
    ("Assets", "image"): (0, "path"),
    ("assets", "image"): (0, "path"),
    ("Assets", "font"): (0, "path"),
    ("assets", "font"): (0, "path"),
    ("Assets", "sprite_sheet"): (0, "path"),
    ("assets", "sprite_sheet"): (0, "path"),
    ("Audio", "load_sound"): (0, "path"),
    ("audio", "load_sound"): (0, "path"),
    ("Audio", "load_music"): (0, "path"),
    ("audio", "load_music"): (0, "path"),
}


def _result(
    path: str,
    lineno: int | None,
    column: int | None,
    message: str,
    *,
    severity: str,
    code: str,
    category: str,
) -> CheckResult:
    return CheckResult(
        path, lineno, column, message, severity=severity, code=code, category=category
    )


# -- syntax ----------------------------------------------------------------


def check_syntax(path: str, source: str) -> list[CheckResult]:
    """Report a ``SYNTAX001`` for invalid Python, or an empty list."""
    try:
        compile(source, path, "exec")
    except SyntaxError as exc:
        return [
            _result(
                path,
                exc.lineno,
                exc.offset,
                exc.msg if exc.msg else str(exc),
                severity=SEVERITY_ERROR,
                code="SYNTAX001",
                category=CATEGORY_SYNTAX,
            )
        ]
    except ValueError as exc:
        # e.g. an embedded null byte; still an error, still SYNTAX001.
        return [
            _result(
                path,
                None,
                None,
                str(exc),
                severity=SEVERITY_ERROR,
                code="SYNTAX001",
                category=CATEGORY_SYNTAX,
            )
        ]
    return []


def check_read_failure(path: str, error: BaseException) -> list[CheckResult]:
    """Report a ``PROJECT001`` when a source file could not be read."""
    return [
        _result(
            path,
            None,
            None,
            f"could not read file: {error}",
            severity=SEVERITY_WARNING,
            code="PROJECT001",
            category=CATEGORY_PROJECT,
        )
    ]


# -- imports ---------------------------------------------------------------


def check_imports(path: str, source: str, tree: ast.Module) -> list[CheckResult]:
    """Report ``IMPORT001`` for imports from ``pydex_ge`` that do not exist."""
    results: list[CheckResult] = []
    api = top_level_names()
    submodules = submodule_names()
    members = submodule_member_names()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(
            "pydex_ge"
        ):
            parts = node.module.split(".")
            if len(parts) >= 2:
                sub = parts[1]
                if sub not in submodules:
                    suggestion = _nearest(sub, submodules)
                    message = f"Cannot import {node.module!r}: no such PYDEX submodule."
                    if suggestion and suggestion != sub:
                        message += f" Did you mean 'pydex_ge.{suggestion}'?"
                    results.append(
                        _result(
                            path,
                            node.lineno,
                            node.col_offset + 1,
                            message,
                            severity=SEVERITY_ERROR,
                            code="IMPORT001",
                            category=CATEGORY_IMPORT,
                        )
                    )
                    continue
                sub_members = members.get(sub, set())
                for alias in node.names:
                    name = alias.name
                    if name == "*":
                        continue
                    if name in sub_members:
                        continue
                    suggestion = _nearest(name, sub_members) if sub_members else ""
                    message = f"Cannot import {name!r} from 'pydex_ge.{sub}'."
                    if suggestion:
                        message += f" Did you mean {suggestion!r}? PYDEX does not"
                        message += " export this name."
                    elif sub_members:
                        message += " PYDEX does not export this name."
                    else:
                        # No reliable member list for this submodule: silence.
                        continue
                    results.append(
                        _result(
                            path,
                            node.lineno,
                            node.col_offset + 1,
                            message,
                            severity=SEVERITY_ERROR,
                            code="IMPORT001",
                            category=CATEGORY_IMPORT,
                        )
                    )
            else:
                # ``from pydex_ge import Name as Alias``: check the imported
                # name itself, not the local alias.
                for alias in node.names:
                    name = alias.name
                    if name == "*" or name == "__version__":
                        continue
                    if name in api:
                        continue
                    suggestion = _nearest(name, api)
                    message = f"Cannot import {name!r} from 'pydex_ge'."
                    if suggestion:
                        message += f" Did you mean {suggestion!r}? PYDEX does not export"
                        message += " this name."
                    else:
                        message += " PYDEX does not export this name."
                    results.append(
                        _result(
                            path,
                            node.lineno,
                            node.col_offset + 1,
                            message,
                            severity=SEVERITY_ERROR,
                            code="IMPORT001",
                            category=CATEGORY_IMPORT,
                        )
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "pydex_ge" and len(parts) > 1:
                    sub = parts[1]
                    if sub in submodules:
                        continue
                    suggestion = _nearest(sub, submodules)
                    message = f"Cannot import {alias.name!r}: 'pydex_ge.{sub}' does not exist."
                    if suggestion and suggestion != sub:
                        message += f" Did you mean 'pydex_ge.{suggestion}'?"
                    results.append(
                        _result(
                            path,
                            node.lineno,
                            node.col_offset + 1,
                            message,
                            severity=SEVERITY_ERROR,
                            code="IMPORT001",
                            category=CATEGORY_IMPORT,
                        )
                    )
    return results


# -- undefined names -------------------------------------------------------


class _Scope:
    """Tracks defined names inside one lexical scope chain."""

    def __init__(self) -> None:
        self.names: set[str] = set()
        self.children: list[_Scope] = []

    def add(self, name: str) -> None:
        if name:
            self.names.add(name)

    def all_names(self) -> set[str]:
        merged = set(self.names)
        for child in self.children:
            merged |= child.all_names()
        return merged


def _collect_definitions(tree: ast.Module) -> _Scope:
    """Walk the tree and record every name that is (re)assigned or imported.

    We deliberately over-approximate: any assignment anywhere in the file
    counts as 'defined', so code that assigns in one branch and reads in
    another is not flagged.  Only clearly-undefined reads are reported.
    """
    root = _Scope()
    stack = [root]

    def defined(name: str) -> None:
        for scope in stack:
            if name in scope.names:
                return
        stack[-1].add(name)

    class Collector(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                defined(alias.asname or alias.name.split(".")[0])
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            for alias in node.names:
                defined(alias.asname or alias.name)
            self.generic_visit(node)

        def visit_Global(self, node):
            for name in node.names:
                defined(name)
            self.generic_visit(node)

        def visit_Nonlocal(self, node):
            for name in node.names:
                defined(name)

        def visit_FunctionDef(self, node):
            self._enter_scope()
            try:
                defined(node.name)
                self._collect_args(node.args)
                self.generic_visit(node)
            finally:
                stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node):
            self._enter_scope()
            try:
                self._collect_args(node.args)
                self.generic_visit(node)
            finally:
                stack.pop()

        def visit_ClassDef(self, node):
            defined(node.name)
            self._enter_scope()
            try:
                self.generic_visit(node)
            finally:
                stack.pop()

        def visit_Name(self, node):
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                defined(node.id)
            self.generic_visit(node)

        def visit_ExceptHandler(self, node):
            if node.name:
                self._enter_scope()
                try:
                    child = _Scope()
                    child.add(node.name)
                    stack[-1].children.append(child)
                    stack.append(child)
                    self.generic_visit(node)
                finally:
                    stack.pop()
            else:
                self.generic_visit(node)

        def _enter_scope(self) -> _Scope:
            child = _Scope()
            stack[-1].children.append(child)
            stack.append(child)
            return child

        def _collect_args(self, args: ast.arguments) -> None:
            for group in (args.posonlyargs, args.args, args.kwonlyargs):
                for arg in group:
                    stack[-1].add(arg.arg)
            if args.vararg is not None:
                stack[-1].add(args.vararg.arg)
            if args.kwarg is not None:
                stack[-1].add(args.kwarg.arg)

    Collector().visit(tree)
    return root


def check_names(path: str, source: str, tree: ast.Module) -> list[CheckResult]:
    """Report ``NAME001`` for names that look undefined, conservatively.

    Also reports ``PYDEX001`` when the undefined name is a near-miss of a
    real PYDEX API name (``Camra2D`` -> ``Camera2D``).
    """
    if any(
        isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names)
        for node in ast.walk(tree)
    ):
        return []  # Star imports make static name checking unreliable.

    definitions = _collect_definitions(tree).all_names()
    known = known_api_members()
    results: list[CheckResult] = []
    defined_here = set(definitions)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Name):
            continue
        if not isinstance(node.ctx, ast.Load):
            continue
        name = node.id
        if name in defined_here or name in _BUILTINS or name in _GLOBAL_NAMES:
            continue
        if name in _SAFE_NAMES:
            continue
        if name.startswith("__") and name.endswith("__"):
            continue

        if name in known:
            continue  # e.g. used via a wildcard or a known PYDEX name.

        suggestion = _nearest(name, known)
        if suggestion:
            results.append(
                _result(
                    path,
                    node.lineno,
                    node.col_offset + 1,
                    f"Unknown PYDEX name: {name}.  Did you mean: {suggestion}?",
                    severity=SEVERITY_ERROR,
                    code="PYDEX001",
                    category=CATEGORY_PYDEX,
                )
            )
            continue

        results.append(
            _result(
                path,
                node.lineno,
                node.col_offset + 1,
                f"Possible undefined name: {name}",
                severity=SEVERITY_WARNING,
                code="NAME001",
                category=CATEGORY_NAME,
            )
        )
    return results


# -- PYDEX API / configuration / scenes ------------------------------------


def check_pydex_usage(path: str, source: str, tree: ast.Module) -> list[CheckResult]:
    """Flag obvious misuse of the PYDEX API, statically.

    * ``PYDEX001``   unknown PYDEX name used as a ``pydex_ge.X(...)`` call
                     (``pydex_ge.Camra2D()`` -> ``Camera2D``).
    * ``PYDEX002``   attribute access on a known PYDEX *class* used directly
                     (``Sprite.move()`` where ``move`` is not public).  Only
                     class-level access is checked: instance attributes set
                     in ``__init__`` and subclass members make per-instance
                     checks unreliable, and the spec says to report nothing
                     when unsure.
    * ``CONFIG001``  clearly-invalid constructor arguments, e.g.
                     ``Camera3D(fov="90")`` or ``Game(fps="60")``.
    * ``SCENE001``   ``SceneManager.push()`` receiving a non-Scene literal.
    """
    results: list[CheckResult] = []
    class_to_type = _class_members()
    exposed_names = top_level_names()

    # 0. ``pydex_ge.<Unknown>()`` where the name is not in the public API.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "pydex_ge" and func.attr not in exposed_names:
                suggestion = _nearest(func.attr, exposed_names)
                message = f"Unknown PYDEX name: {func.attr}."
                if suggestion:
                    message += f"  Did you mean: {suggestion}?"
                results.append(
                    _result(
                        path,
                        node.lineno,
                        func.col_offset + 1,
                        message,
                        severity=SEVERITY_ERROR,
                        code="PYDEX001",
                        category=CATEGORY_PYDEX,
                    )
                )

    # 1. Dotted names on a known PYDEX class used directly:
    #    ``Sprite.move(...)`` where ``move`` is not a public member.
    #    Instance tracking is deliberately avoided: instance attributes set
    #    in ``__init__`` (``self.x``) and subclass members make those checks
    #    unreliable, and the spec says to report nothing when unsure.
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            owner_name = node.value.id
            if owner_name in class_to_type:
                members = class_to_type[owner_name]
                if node.attr not in members:
                    suggestion = _nearest(node.attr, members)
                    message = f"{owner_name} has no attribute {node.attr!r}."
                    if suggestion:
                        message += f" Did you mean {suggestion!r}?"
                    results.append(
                        _result(
                            path,
                            node.lineno,
                            node.col_offset + 1,
                            message,
                            severity=SEVERITY_ERROR,
                            code="PYDEX002",
                            category=CATEGORY_PYDEX,
                        )
                    )

    # 3. Constructor argument checks.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        callee = _callee_name(func)
        if callee is not None and callee in exposed_names:
            _check_constructor(path, node, callee, results)
        _check_scene_push(path, node, results)

    return results


def _callee_name(func: ast.AST) -> str | None:
    """The plain class/function name behind ``Foo(...)`` or ``pydex_ge.Foo(...)``."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == "pydex_ge":
            return func.attr
    return None


_SCENE_RECEIVERS = ("scenes", "manager", "scene_manager")


def _check_scene_push(path: str, node: ast.Call, results: list[CheckResult]) -> None:
    """Flag ``SceneManager.push(<non-scene literal>)``, e.g. ``push('Menu')``.

    Conservative: only fires when the receiver looks like a scene manager
    (``game.scenes.push``, ``scenes.push``, ``manager.push``) and the first
    positional argument is a string literal.
    """
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "push":
        return
    if not node.args:
        return
    first = node.args[0]
    if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        return
    receiver = func.value
    is_manager = False
    if isinstance(receiver, ast.Name) and receiver.id in _SCENE_RECEIVERS:
        is_manager = True
    elif isinstance(receiver, ast.Attribute) and receiver.attr in _SCENE_RECEIVERS:
        is_manager = True
    if not is_manager:
        return
    results.append(
        _result(
            path,
            node.lineno,
            first.col_offset + 1,
            "SceneManager.push() expects a Scene instance, got "
            f"{first.value!r}.",
            severity=SEVERITY_ERROR,
            code="SCENE001",
            category=CATEGORY_SCENE,
        )
    )


def _class_members() -> dict[str, set[str]]:
    """Public attribute names of known PYDEX classes (best effort)."""
    members: dict[str, set[str]] = {}
    names = ("Sprite", "Camera", "Camera2D", "Camera3D", "Scene", "Text", "Label")
    for name in names:
        try:
            cls = getattr(_load_pydex(), name)
        except Exception:  # pydex_ge not importable in this environment
            continue
        members[name] = {m for m in dir(cls) if not m.startswith("_")}
    return members


def _load_pydex():  # pragma: no cover - exercised in normal usage
    import pydex_ge

    return pydex_ge


def _check_constructor(
    path: str,
    node: ast.Call,
    callee: str,
    results: list[CheckResult],
) -> None:
    """Validate obvious literal arguments for the known constructors."""
    if callee in ("Camera3D", "Camera", "Camera2D"):
        for kw in node.keywords:
            if kw.arg in ("fov", "zoom") and _is_constant(kw.value):
                value = _const_value(kw.value)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if kw.arg == "fov" and not 1.0 <= float(value) <= 179.0:
                        results.append(
                            _result(
                                path,
                                node.lineno,
                                kw.value.col_offset + 1,
                                f"{callee} fov must be between 1 and 179 degrees, "
                                f"got {value!r}.",
                                severity=SEVERITY_ERROR,
                                code="CONFIG001",
                                category=CATEGORY_CONFIGURATION,
                            )
                        )
                    elif kw.arg == "zoom" and float(value) <= 0:
                        results.append(
                            _result(
                                path,
                                node.lineno,
                                kw.value.col_offset + 1,
                                f"{callee} zoom must be greater than zero, got {value!r}.",
                                severity=SEVERITY_ERROR,
                                code="CONFIG001",
                                category=CATEGORY_CONFIGURATION,
                            )
                        )
                elif isinstance(value, str):
                    label = "fov" if kw.arg == "fov" else "zoom"
                    results.append(
                        _result(
                            path,
                            node.lineno,
                            kw.value.col_offset + 1,
                            f"{callee} {label} must be a number, got {value!r}.",
                            severity=SEVERITY_ERROR,
                            code="CONFIG001",
                            category=CATEGORY_CONFIGURATION,
                        )
                    )
    elif callee == "Game":
        for kw in node.keywords:
            if kw.arg == "fps" and _is_constant(kw.value):
                value = _const_value(kw.value)
                if value in (None, True):
                    continue
                if isinstance(value, (int, float)) and value > 0:
                    continue
                results.append(
                    _result(
                        path,
                        node.lineno,
                        kw.value.col_offset + 1,
                        "fps must be a positive number or None for unlimited.",
                        severity=SEVERITY_ERROR,
                        code="CONFIG001",
                        category=CATEGORY_CONFIGURATION,
                    )
                )


def _is_constant(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return isinstance(node.operand, ast.Constant)
    return False


def _const_value(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = node.operand.value  # type: ignore[attr-defined]
        return -value if isinstance(node.op, ast.USub) else value
    return None


# -- assets ----------------------------------------------------------------


def check_asset_paths(
    path: str,
    source: str,
    tree: ast.Module,
    project_root: str | None,
) -> list[CheckResult]:
    """Resolve literal asset paths in PYDEX asset-loading calls.

    * ``ASSET001`` literal path that does not exist anywhere reachable.
    * ``ASSET002`` dynamic asset path (a variable) that cannot be verified.
    """
    results: list[CheckResult] = []
    base_dir = os.path.dirname(os.path.abspath(path)) if path else None
    search_roots = [base_dir, project_root, os.getcwd()]
    search_roots = [r for r in search_roots if r]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        key = _call_key(node)
        if key not in _ASSET_CALLS:
            continue
        arg_index, arg_name = _ASSET_CALLS[key]
        arg = None
        if len(node.args) > arg_index:
            arg = node.args[arg_index]
        else:
            for kw in node.keywords:
                if kw.arg == arg_name:
                    arg = kw.value
                    break
        if arg is None:
            continue
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            literal = arg.value
            if _find_asset(literal, search_roots):
                continue
            message = f"Missing asset: {os.path.basename(literal)}"
            if literal != os.path.basename(literal):
                message += f" ({literal!r})"
            results.append(
                _result(
                    path,
                    node.lineno,
                    arg.col_offset + 1,
                    message,
                    severity=SEVERITY_ERROR,
                    code="ASSET001",
                    category=CATEGORY_ASSET,
                )
            )
        elif isinstance(arg, ast.Name):
            # Dynamic path: cannot verify statically.
            results.append(
                _result(
                    path,
                    node.lineno,
                    arg.col_offset + 1,
                    f"Asset path is dynamic ({arg.id!r}); it cannot be verified.",
                    severity=SEVERITY_INFO,
                    code="ASSET002",
                    category=CATEGORY_ASSET,
                )
            )
    return results


def _call_key(node: ast.Call):
    func = node.func
    if isinstance(func, ast.Name):
        return (func.id, None)
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == "pydex_ge":
            return (func.attr, None)
        return (func.value.id, func.attr)
    return None


def _find_asset(literal: str, search_roots: list[str]) -> bool:
    path = os.path.expandvars(os.path.expanduser(literal))
    if os.path.isabs(path):
        return os.path.isfile(path)
    for root in search_roots:
        if root and os.path.isfile(os.path.join(root, path)):
            return True
    return False


def _nearest(name: str, candidates: set[str] | list[str]) -> str | None:
    """Best difflib near-miss for ``name``, or None when nothing is close."""
    matches = difflib.get_close_matches(name, sorted(candidates), n=1, cutoff=0.7)
    return matches[0] if matches else None


__all__ = [
    "check_asset_paths",
    "check_imports",
    "check_names",
    "check_pydex_usage",
    "check_read_failure",
    "check_syntax",
]