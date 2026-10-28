"""Project file discovery for the PYDEX project checker.

Handles the walk over a project folder: which directories/files are visited,
which are skipped (hidden folders, vendor caches, ``.pydexignore``), the
list of Python source files, and the list of asset files.  Everything is
headless and reads only file paths / names — it never opens windows or
imports user code.
"""

from __future__ import annotations

import fnmatch
import os

PYTHON_EXTENSIONS = (".py", ".pyw")

ASSET_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".ttf",
    ".otf",
    ".wav",
    ".ogg",
    ".mp3",
}

# Directories the checker always stays out of.
_SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "site-packages",
    ".pytest_cache",
    ".mypy_cache",
    ".opencode",
    "dist",
    "build",
    "egg-info",
    ".egg-info",
}


def read_ignore_patterns(root: str) -> list[str]:
    """Read ``.pydexignore`` next to ``root``, if present.

    Each non-empty, non-comment line is a glob pattern matched against the
    project-relative path (using forward slashes).  A trailing ``/`` marks a
    directory pattern that also stops descent into that folder.
    """
    ignore_path = os.path.join(root, ".pydexignore")
    patterns: list[str] = []
    try:
        with open(ignore_path, "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line.replace("\\", "/"))
    except OSError:
        return patterns
    return patterns


def _matches(pattern: str, relpath: str) -> bool:
    """Whether ``relpath`` (forward-slash, no leading slash) matches ``pattern``."""
    normalized = pattern.rstrip("/")
    if pattern.endswith("/"):
        # A directory pattern: matches this path or anything beneath it.
        return relpath.startswith(normalized + "/") or relpath == normalized
    return fnmatch.fnmatch(relpath, normalized)


def iter_project_files(root: str, *, include_assets: bool = False):
    """Yield ``(relpath, abspath)`` for every interesting file under ``root``.

    Skips hidden directories, common vendor/cache folders, and anything
    matched by a ``.pydexignore`` file next to the project root.  When
    ``include_assets`` is set, files with a known asset extension are included
    too; Python files (``.py`` / ``.pyw``) are always included.
    """
    root = os.path.abspath(root)
    ignore_patterns = read_ignore_patterns(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        kept: list[str] = []
        for name in dirnames:
            rel = _rel(root, os.path.join(dirpath, name))
            if name.startswith("."):
                continue
            if name in _SKIP_DIRS:
                continue
            if any(_matches(p, rel) for p in ignore_patterns):
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            ext = os.path.splitext(name)[1].lower()
            is_python = ext in PYTHON_EXTENSIONS
            is_asset = include_assets and ext in ASSET_EXTENSIONS
            if not (is_python or is_asset):
                continue
            full = os.path.join(dirpath, name)
            rel = _rel(root, full)
            if any(_matches(p, rel) for p in ignore_patterns):
                continue
            yield rel, full


def iter_python_files(root: str):
    """Yield ``(relpath, abspath)`` for every ``.py``/``.pyw`` under ``root``."""
    for rel, full in iter_project_files(root, include_assets=False):
        if os.path.splitext(rel)[1].lower() in PYTHON_EXTENSIONS:
            yield rel, full


def iter_asset_files(root: str):
    """Yield ``(relpath, abspath)`` for every asset file under ``root``."""
    for rel, full in iter_project_files(root, include_assets=True):
        if os.path.splitext(rel)[1].lower() in ASSET_EXTENSIONS:
            yield rel, full


def _rel(root: str, fullpath: str) -> str:
    rel = os.path.relpath(fullpath, root)
    return rel.replace("\\", "/")


def _public_path(path: str) -> str:
    """A display path for the report: relative to ``os.getcwd`` when possible."""
    try:
        return os.path.relpath(path, os.getcwd()).replace("\\", "/")
    except ValueError:
        return path.replace("\\", "/")


__all__ = [
    "ASSET_EXTENSIONS",
    "PYTHON_EXTENSIONS",
    "iter_asset_files",
    "iter_project_files",
    "iter_python_files",
    "read_ignore_patterns",
]