"""Project model for the PYDEX editor (dex-editor).

A :class:`DexProject` is a folder on disk holding an ``assets/``
directory, a ``scenes/`` directory for user-generated scene code, a
generated ``main.py`` and a small JSON manifest (``project.pydex_ge.json``).

The manifest is the source of truth for the visual state: which assets
exist and where sprites are placed.  It is the interchange file the
editor writes on save and reads on open, so it stays small, versioned
and hand-editable.
"""

from __future__ import annotations

import json
import os

from ..exceptions import ConfigurationError

MANIFEST_NAME = "project.pydex_ge.json"
PROJECT_VERSION = 1

IMAGE_EXTENSIONS = (".png", ".bmp", ".jpg", ".jpeg", ".gif")
AUDIO_EXTENSIONS = (".wav", ".ogg", ".mp3", ".flac")

_ASSET_KINDS = {"image", "audio"}


def _slug(value: object) -> str:
    """Coerce a project / scene name to a valid Python identifier."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("Name must be a non-empty string.")
    cleaned = "".join(
        char if char.isalnum() or char == "_" else "_" for char in value.strip()
    )
    if cleaned[0].isdigit():
        cleaned = "scene_" + cleaned
    if not cleaned:
        raise ConfigurationError("Name must contain at least one letter or digit.")
    return cleaned


def asset_kind(filename: str) -> str:
    """Return ``'image'`` or ``'audio'`` for a filename's extension."""
    if not isinstance(filename, str) or not filename.strip():
        raise ConfigurationError("Asset filename must be a non-empty string.")
    ext = os.path.splitext(filename)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    raise ConfigurationError(
        f"Unsupported asset extension {ext!r} (expected image or audio)."
    )


class AssetEntry:
    """A file imported into a project's ``assets/`` directory."""

    __slots__ = ("kind", "filename")

    def __init__(self, kind: str, filename: str) -> None:
        if kind not in _ASSET_KINDS:
            raise ConfigurationError(f"Unknown asset kind {kind!r}.")
        if not isinstance(filename, str) or not filename.strip():
            raise ConfigurationError("Asset filename must be a non-empty string.")
        self.kind = kind
        self.filename = filename

    @property
    def display_name(self) -> str:
        return os.path.basename(self.filename)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "filename": self.filename}

    @classmethod
    def from_dict(cls, data: dict) -> AssetEntry:
        if not isinstance(data, dict):
            raise ConfigurationError("Asset entries must be JSON objects.")
        kind = data.get("kind")
        filename = data.get("filename")
        if kind not in _ASSET_KINDS:
            raise ConfigurationError(f"Unknown asset kind {kind!r}.")
        if not isinstance(filename, str) or not filename.strip():
            raise ConfigurationError("Asset filename must be a non-empty string.")
        return cls(kind, filename)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, AssetEntry)
            and self.kind == other.kind
            and self.filename == other.filename
        )

    def __repr__(self) -> str:
        return f"<AssetEntry {self.kind}:{self.filename}>"


class SpriteEntry:
    """A placed image in a scene."""

    __slots__ = ("asset", "x", "y", "layer", "scale", "flip_h", "flip_v", "visible")

    def __init__(
        self,
        asset: str,
        *,
        x: float = 0.0,
        y: float = 0.0,
        layer: int = 0,
        scale=1.0,
        flip_h: bool = False,
        flip_v: bool = False,
        visible: bool = True,
    ) -> None:
        if not isinstance(asset, str) or not asset.strip():
            raise ConfigurationError("Sprite asset must be a non-empty string.")
        self.asset = asset
        self.x = _finite(x, "x")
        self.y = _finite(y, "y")
        self.layer = _int(layer, "layer")
        self.scale = _scale(scale)
        self.flip_h = bool(flip_h)
        self.flip_v = bool(flip_v)
        self.visible = bool(visible)

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "x": self.x,
            "y": self.y,
            "layer": self.layer,
            "scale": list(self.scale) if isinstance(self.scale, tuple) else self.scale,
            "flip_h": self.flip_h,
            "flip_v": self.flip_v,
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SpriteEntry:
        if not isinstance(data, dict):
            raise ConfigurationError("Sprite entries must be JSON objects.")
        return cls(
            data["asset"],
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            layer=data.get("layer", 0),
            scale=data.get("scale", 1.0),
            flip_h=data.get("flip_h", False),
            flip_v=data.get("flip_v", False),
            visible=data.get("visible", True),
        )

    def __repr__(self) -> str:
        return f"<SpriteEntry {self.asset} at ({self.x}, {self.y})>"


class SceneEntry:
    """A named scene holding placed sprites."""

    __slots__ = ("name", "width", "height", "grid", "sprites")

    def __init__(
        self,
        name: str,
        *,
        width: float = 1600.0,
        height: float = 1200.0,
        grid: float = 32.0,
    ) -> None:
        self.name = _ident(name)
        self.width = _finite(width, "width")
        self.height = _finite(height, "height")
        self.grid = _finite(grid, "grid")
        self.sprites: list[SpriteEntry] = []

    def add_sprite(self, sprite: SpriteEntry) -> None:
        self.sprites.append(sprite)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "grid": self.grid,
            "sprites": [sprite.to_dict() for sprite in self.sprites],
        }

    @classmethod
    def from_dict(cls, data: dict) -> SceneEntry:
        if not isinstance(data, dict):
            raise ConfigurationError("Scene entries must be JSON objects.")
        scene = cls(
            data["name"],
            width=data.get("width", 1600.0),
            height=data.get("height", 1200.0),
            grid=data.get("grid", 32.0),
        )
        sprites = data.get("sprites", [])
        if isinstance(sprites, list):
            for item in sprites:
                scene.sprites.append(SpriteEntry.from_dict(item))
        return scene

    def __repr__(self) -> str:
        return f"<SceneEntry {self.name} ({len(self.sprites)} sprites)>"


class DexProject:
    """An editor project rooted at a directory."""

    def __init__(
        self,
        root: str,
        name: str,
        *,
        assets=None,
        scenes=None,
    ) -> None:
        if not isinstance(root, str) or not root.strip():
            raise ConfigurationError("Project root must be a non-empty path.")
        self.root = os.path.abspath(root)
        self.name = _ident(name)
        self.assets: list[AssetEntry] = list(assets or [])
        self.scenes: list[SceneEntry] = list(scenes or [])
        self.dirty = False

    # -- constructors ------------------------------------------------------

    @classmethod
    def create_empty(cls, root: str, name: str) -> DexProject:
        """Create a fresh project on disk and return it.

        Refuses to write into a non-empty, non-project directory.
        """
        root = os.path.abspath(root)
        existing = os.listdir(root) if os.path.isdir(root) else []
        foreign = [name for name in existing if name != MANIFEST_NAME]
        if foreign:
            raise ConfigurationError(
                f"Directory {root!r} is not empty; refusing to create a project here."
            )
        os.makedirs(os.path.join(root, "assets"), exist_ok=True)
        os.makedirs(os.path.join(root, "scenes"), exist_ok=True)
        project = cls(root, name)
        project.scenes.append(SceneEntry("Main"))
        project.save()
        project.write_starter_code()
        return project

    @classmethod
    def load(cls, root: str) -> DexProject:
        """Load a project from its manifest."""
        root = os.path.abspath(root)
        manifest_path = os.path.join(root, MANIFEST_NAME)
        if not os.path.isfile(manifest_path):
            raise ConfigurationError(
                f"No project manifest found at {manifest_path!r}."
            )
        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except ValueError as exc:
            raise ConfigurationError(
                f"Project manifest {manifest_path!r} is not valid JSON: {exc}"
            )
        if not isinstance(data, dict):
            raise ConfigurationError("Project manifest must be a JSON object.")
        version = data.get("version")
        if version != PROJECT_VERSION:
            raise ConfigurationError(
                f"Unsupported project version {version!r} (this build supports "
                f"version {PROJECT_VERSION})."
            )
        assets = [AssetEntry.from_dict(item) for item in data.get("assets", [])]
        scenes = [SceneEntry.from_dict(item) for item in data.get("scenes", [])]
        return cls(root, data["name"], assets=assets, scenes=scenes)

    # -- filesystem helpers -------------------------------------------------

    @property
    def manifest_path(self) -> str:
        return os.path.join(self.root, MANIFEST_NAME)

    @property
    def main_path(self) -> str:
        return os.path.join(self.root, "main.py")

    def assets_dir(self) -> str:
        directory = os.path.join(self.root, "assets")
        os.makedirs(directory, exist_ok=True)
        return directory

    def asset_path(self, filename: str) -> str:
        """Absolute path to ``assets/<filename>``."""
        if not isinstance(filename, str) or "/" in filename or "\\" in filename:
            raise ConfigurationError(f"Invalid asset filename {filename!r}.")
        return os.path.join(self.assets_dir(), filename)

    # -- scene helpers --------------------------------------------------------

    def scene(self, name: str) -> SceneEntry | None:
        target = _slug(name)
        for scene in self.scenes:
            if _slug(scene.name) == target:
                return scene
        return None

    def add_scene(self, name: str) -> SceneEntry:
        if self.scene(name) is not None:
            raise ConfigurationError(f"Scene {name!r} already exists.")
        scene = SceneEntry(name)
        self.scenes.append(scene)
        self.dirty = True
        return scene

    def remove_scene(self, name: str) -> bool:
        target = _slug(name)
        for index, scene in enumerate(self.scenes):
            if _slug(scene.name) == target:
                del self.scenes[index]
                self.dirty = True
                return True
        return False

    # -- asset helpers --------------------------------------------------------

    def asset(self, filename: str) -> AssetEntry | None:
        for entry in self.assets:
            if entry.filename == filename:
                return entry
        return None

    def import_asset(self, source_path: str) -> AssetEntry:
        """Copy a file into ``assets/`` and register it in the manifest.

        When a file with the same bytes already exists it is reused, so
        re-importing does not create duplicates.
        """
        if not isinstance(source_path, str) or not source_path.strip():
            raise ConfigurationError("Asset source path must be a non-empty string.")
        source_path = os.path.abspath(source_path)
        if not os.path.isfile(source_path):
            raise ConfigurationError(f"Asset source does not exist: {source_path!r}.")
        filename = os.path.basename(source_path)
        kind = asset_kind(filename)
        with open(source_path, "rb") as handle:
            content = handle.read()
        existing = self.asset(filename)
        if existing is not None:
            try:
                with open(self.asset_path(filename), "rb") as handle:
                    if handle.read() == content:
                        return existing
            except OSError:
                pass
        if existing is None:
            target = self.asset_path(filename)
        else:
            stem, extension = os.path.splitext(filename)
            counter = 2
            while True:
                candidate = f"{stem}-{counter}{extension}"
                if self.asset(candidate) is None:
                    target = self.asset_path(candidate)
                    filename = candidate
                    break
                counter += 1
        with open(target, "wb") as handle:
            handle.write(content)
        entry = AssetEntry(kind, filename)
        self.assets.append(entry)
        self.dirty = True
        return entry

    def remove_asset(self, filename: str) -> bool:
        """Remove an asset entry and its file (sprites keep pointing at the missing name)."""
        entry = self.asset(filename)
        if entry is None:
            return False
        self.assets.remove(entry)
        try:
            os.remove(self.asset_path(filename))
        except OSError:
            pass
        self.dirty = True
        return True

    # -- persistence ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "version": PROJECT_VERSION,
            "name": self.name,
            "assets": [entry.to_dict() for entry in self.assets],
            "scenes": [scene.to_dict() for scene in self.scenes],
        }

    def save(self) -> str:
        """Write the manifest and return its path."""
        payload = json.dumps(self.to_dict(), indent=2, sort_keys=True)
        with open(self.manifest_path, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
        self.dirty = False
        return self.manifest_path

    def write_starter_code(self) -> str:
        """Write the initial human-editable ``main.py`` if absent."""
        from . import codegen

        if os.path.exists(self.main_path):
            return self.main_path
        with open(self.main_path, "w", encoding="utf-8") as handle:
            handle.write(codegen.generate_main(self))
        return self.main_path


def _ident(value: object) -> str:
    cleaned = _slug(value)
    if cleaned in {"class", "def", "import", "from", "pass", "return"}:
        raise ConfigurationError(f"Name {value!r} is a Python keyword.")
    return cleaned


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ConfigurationError(f"{name} must be finite, got {value!r}.")
    return number


def _scale(value: object) -> float | tuple[float, float]:
    """A uniform float scale or a per-axis ``(sx, sy)`` pair (finite)."""
    if isinstance(value, bool):
        raise ConfigurationError(f"Invalid scale {value!r}.")
    if isinstance(value, (int, float)):
        return _finite(value, "scale")
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return (_finite(value[0], "scale[sx]"), _finite(value[1], "scale[sy]"))
    raise ConfigurationError(
        f"scale must be a number or an (sx, sy) pair, got {value!r}."
    )


def _int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer, got {value!r}.")
    return value


__all__ = [
    "DexProject",
    "AssetEntry",
    "SceneEntry",
    "SpriteEntry",
    "asset_kind",
    "IMAGE_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "MANIFEST_NAME",
    "PROJECT_VERSION",
]