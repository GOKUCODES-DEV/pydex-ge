"""A static registry of PYDEX's public API for the project checker.

The checker never imports a user's project and never opens a window; it only
needs to know *what PYDEX exports* so it can flag ``from pydex_ge import Spritee``
or a bare typo like ``Camra2D()``.  This module builds that table two ways:

* top-level names: taken from ``pydex_ge``'s ``__all__`` when available,
  falling back to the hardcoded list below;
* submodules: discovered by listing the ``pydex_ge`` package directory.

No user code is executed and no window is opened.
"""

from __future__ import annotations

import ast
import os

try:  # best effort: the real public surface
    import pydex_ge as _pydex

    def _public_names() -> tuple[str, ...]:
        # Read lazily: during the package's own import the checker is
        # imported before ``pydex_ge.__all__`` is assigned.
        names = getattr(_pydex, "__all__", ())
        return tuple(names) if names else _HARDCODED_TOP_LEVEL
except Exception:  # pragma: no cover - package not importable here
    _pydex = None

    def _public_names() -> tuple[str, ...]:
        return _HARDCODED_TOP_LEVEL

_HARDCODED_TOP_LEVEL = (
    "__version__",
    "Animation",
    "Assets",
    "Audio",
    "BackendError",
    "Body",
    "Camera",
    "Camera2D",
    "Camera3D",
    "check_all",
    "check_assets",
    "check_file",
    "check_project",
    "check_pydex",
    "check_python",
    "Clock",
    "ConfigurationError",
    "DirectionalLight",
    "Event",
    "EventManager",
    "EventType",
    "Font",
    "format_error",
    "format_result",
    "Game",
    "Image",
    "Input",
    "Keys",
    "Label",
    "Material",
    "Mesh",
    "MissingAssetError",
    "Music",
    "Object3D",
    "Parallax",
    "PydexError",
    "Quaternion",
    "Rect",
    "Renderer",
    "Scene",
    "SceneManager",
    "Sound",
    "Sprite",
    "SpriteSheet",
    "SplashScreen",
    "Text",
    "Texture",
    "TextureRegion",
    "TileMap",
    "Transform2D",
    "Transform3D",
    "Vector2",
    "Vector3",
    "Window",
    "World",
)

# Things that look like API names but are checker-only helpers / errors.
# Deliberately *not* part of the real ``pydex_ge`` public surface (they live
# in ``pydex_ge.check``), so ``from pydex_ge import X`` for these is flagged.
_EXTRA_PUBLIC_NAMES = {
    "CheckReport",
    "CheckResult",
    "MissingAssetError",
    "PydexError",
    "BackendError",
    "ConfigurationError",
    "Keys",
}

# Known submodules of the ``pydex_ge`` package (checked by importing the
# package so none of them are executed).  If pydex_ge cannot be imported here
# (e.g. a misuse inside the framework), we fall back to the stable list.
_HARDCODED_SUBMODULES = (
    "assets",
    "audio",
    "backend",
    "check",
    "core",
    "exceptions",
    "graphics",
    "input",
    "loading",
    "math",
    "physics",
    "scene",
    "tilemap",
    "transform",
)


def top_level_names() -> set[str]:
    """All names that can be imported from the top-level ``pydex_ge`` module."""
    names = set(_public_names())
    names.update(_EXTRA_PUBLIC_NAMES)
    return names


def submodule_names() -> set[str]:
    """Names of ``pydex_ge`` subpackages/submodules reachable by dotted import."""
    if _pydex is None:  # pragma: no cover
        return set(_HARDCODED_SUBMODULES)
    package_dir = os.path.dirname(os.path.abspath(_pydex.__file__))
    modules: set[str] = set()
    try:
        for entry in os.listdir(package_dir):
            if entry.startswith("_"):
                continue
            subpath = os.path.join(package_dir, entry)
            if os.path.isdir(subpath) and os.path.isfile(
                os.path.join(subpath, "__init__.py")
            ):
                modules.add(entry)
            elif entry.endswith(".py"):
                modules.add(entry[:-3])
    except OSError:  # pragma: no cover
        return set(_HARDCODED_SUBMODULES)
    return modules


def known_api_members() -> set[str]:
    """Every public/module name the checker treats as a valid PYDEX reference."""
    return top_level_names() | submodule_names()


_SUBMODULE_MEMBERS: dict[str, set[str]] | None = None


def submodule_member_names() -> dict[str, set[str]]:
    """Static ``{submodule: public names}`` read from each subpackage's source.

    Names are taken from each submodule's ``__all__`` (falling back to the
    names it defines in ``__init__.py``).  Nothing is imported and no user
    code runs.  Submodules without a resolvable ``__all__`` map to an empty
    set, which callers treat as "cannot verify, say nothing".
    """
    global _SUBMODULE_MEMBERS
    if _SUBMODULE_MEMBERS is not None:
        return _SUBMODULE_MEMBERS
    table: dict[str, set[str]] = {}
    if _pydex is None:  # pragma: no cover - package not importable here
        _SUBMODULE_MEMBERS = table
        return table
    package_dir = os.path.dirname(os.path.abspath(_pydex.__file__))
    for name in submodule_names():
        init = os.path.join(package_dir, name, "__init__.py")
        source_path = init if os.path.isfile(init) else os.path.join(package_dir, name)
        if not source_path.endswith(".py") or not os.path.isfile(source_path):
            continue
        table[name] = _public_names_in_source(source_path)
    _SUBMODULE_MEMBERS = table
    return table


def _public_names_in_source(path: str) -> set[str]:
    """The ``__all__`` list of a source file, or an empty set."""
    try:
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), path)
    except (OSError, SyntaxError):
        return set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            if isinstance(node.value, ast.List):
                return {
                    elt.value
                    for elt in node.value.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                }
    return set()


__all__ = ["known_api_members", "submodule_member_names", "submodule_names", "top_level_names"]