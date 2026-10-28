"""Asset management for PYDEX.

:class:`Assets` is a loader/cache for game assets.  Asking for the same
asset twice returns the same instance, so repeated requests reuse the
cached object instead of re-loading the file:

* :meth:`Assets.image` caches :class:`~pydex_ge.graphics.image.Image` objects,
* :meth:`Assets.font` caches :class:`~pydex_ge.graphics.font.Font` objects
  (keyed by path and size),
* :meth:`Assets.sprite_sheet` caches
  :class:`~pydex_ge.graphics.sprite_sheet.SpriteSheet` objects, sharing the
  underlying cached image with :meth:`Assets.image`.

Paths are normalized to an absolute, case-normalized key, so relative and
absolute forms of the same file map to the same cache entry.

:meth:`Assets.clear` and :meth:`Assets.remove` destroy the backend resources
owned by this manager and empty its caches.  They only ever destroy
resources the manager itself created; resources owned elsewhere (for
example renderer-bound textures) are left untouched.  Cleanup is
idempotent.

Assets never download files and never install fonts into the operating
system.
"""

from __future__ import annotations

import os

from ..backend import select_backend
from ..backend.base import Backend
from ..exceptions import ConfigurationError
from ..graphics.font import Font
from ..graphics.image import Image
from ..graphics.sprite_sheet import SpriteSheet


def _normalize_path(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ConfigurationError("Asset path must be a non-empty string.")
    return os.path.normcase(os.path.abspath(path))


class Assets:
    """A cache of images, fonts, and sprite sheets.

    Parameters
    ----------
    backend:
        Backend used to load assets.  Defaults to SDL2 (or the
        ``PYDEX_BACKEND`` environment variable).

    Textures are deliberately not cached here: a texture belongs to a
    window's renderer and dies with it, so textures are created by the
    renderer (``renderer.create_texture`` or automatically when a sprite is
    drawn), not by the asset cache.
    """

    def __init__(self, *, backend: Backend | None = None) -> None:
        self._backend = backend if backend is not None else select_backend()
        self._images: dict[str, Image] = {}
        self._fonts: dict[tuple[str, int], Font] = {}
        self._sheets: dict[tuple[str, int | None, int | None], SpriteSheet] = {}

    # -- loading ---------------------------------------------------------

    def image(self, path: str) -> Image:
        """Load an image once and return the cached :class:`Image` afterwards."""
        key = _normalize_path(path)
        cached = self._images.get(key)
        if cached is None:
            cached = Image(key, backend=self._backend)
            self._images[key] = cached
        return cached

    def font(self, path: str, size: int = 24) -> Font:
        """Load a font once per ``(path, size)`` and return the cached :class:`Font`."""
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ConfigurationError("Font size must be a positive integer.")
        key = (_normalize_path(path), size)
        cached = self._fonts.get(key)
        if cached is None:
            cached = Font(key[0], size, backend=self._backend)
            self._fonts[key] = cached
        return cached

    def sprite_sheet(
        self,
        path: str,
        cell_width: int | None = None,
        cell_height: int | None = None,
    ) -> SpriteSheet:
        """Load a sprite sheet once and return the cached :class:`SpriteSheet`.

        The sheet wraps the same cached :class:`Image` that
        :meth:`Assets.image` returns for ``path``, so the image is shared
        and never double-loaded or double-freed.
        """
        image_key = _normalize_path(path)
        for value, name in ((cell_width, "cell_width"), (cell_height, "cell_height")):
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                    raise ConfigurationError(
                        f"{name} must be a positive integer or None, got {value!r}."
                    )
        sheet_key = (image_key, cell_width, cell_height)
        cached = self._sheets.get(sheet_key)
        if cached is None:
            cached = SpriteSheet(
                self.image(image_key),
                cell_width=cell_width,
                cell_height=cell_height,
            )
            self._sheets[sheet_key] = cached
        return cached

    # -- queries ---------------------------------------------------------

    def __len__(self) -> int:
        """The total number of cached assets (images, fonts, and sheets)."""
        return len(self._images) + len(self._fonts) + len(self._sheets)

    def contains(self, path: str) -> bool:
        """True if any asset (image, font, or sheet) is cached for ``path``."""
        key = _normalize_path(path)
        if key in self._images:
            return True
        if any(font_key[0] == key for font_key in self._fonts):
            return True
        if any(sheet_key[0] == key for sheet_key in self._sheets):
            return True
        return False

    # -- cleanup ---------------------------------------------------------

    def remove(self, path: str) -> int:
        """Remove every cached asset for ``path``, destroying owned resources.

        Returns the number of cache entries removed (``0`` when nothing was
        cached).  Idempotent.  Removing an image invalidates any sprite
        sheet that shared it.
        """
        key = _normalize_path(path)
        removed = 0

        image = self._images.pop(key, None)
        if image is not None:
            image.destroy()
            removed += 1

        font_keys = [font_key for font_key in self._fonts if font_key[0] == key]
        for font_key in font_keys:
            self._fonts[font_key].destroy()
            del self._fonts[font_key]
            removed += 1

        sheet_keys = [sheet_key for sheet_key in self._sheets if sheet_key[0] == key]
        for sheet_key in sheet_keys:
            del self._sheets[sheet_key]
            removed += 1

        return removed

    def clear(self) -> None:
        """Destroy every cached asset and empty the caches.  Idempotent."""
        for image in self._images.values():
            image.destroy()
        self._images.clear()
        for font in self._fonts.values():
            font.destroy()
        self._fonts.clear()
        self._sheets.clear()


__all__ = ["Assets"]
