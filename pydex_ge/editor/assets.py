"""Asset helpers for the PYDEX editor.

The editor deliberately avoids file-picker machinery (which would drag
in GUI toolkit dependencies), so assets drop into ``assets/`` on disk
--- copied there by :meth:`~pydex_ge.editor.project.DexProject.import_asset`
--- and show up here as soon as they are on disk.
"""

from __future__ import annotations

import os

from .project import DexProject, asset_kind


def scan_assets(project: DexProject) -> list[str]:
    """All files currently in ``assets/`` (registered or not), sorted."""
    directory = project.assets_dir()
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return []
    return [
        name
        for name in names
        if os.path.isfile(os.path.join(directory, name))
    ]


def unregistered(project: DexProject) -> list[str]:
    """Filenames on disk that are not yet in the manifest."""
    registered = {entry.filename for entry in project.assets}
    return [name for name in scan_assets(project) if name not in registered]


def orphaned(project: DexProject) -> list[str]:
    """Registered filenames whose files are no longer on disk."""
    on_disk = set(scan_assets(project))
    return [
        entry.filename
        for entry in project.assets
        if entry.filename not in on_disk
    ]


def kind_of(project: DexProject, filename: str) -> str:
    """Return the asset kind for a file, importing it if needed."""
    entry = project.asset(filename)
    if entry is not None:
        return entry.kind
    return asset_kind(filename)


__all__ = ["scan_assets", "unregistered", "orphaned", "kind_of"]