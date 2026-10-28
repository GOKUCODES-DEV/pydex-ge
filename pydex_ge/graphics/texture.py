"""Textures and texture regions.

A :class:`Texture` is a renderer-owned image ready for drawing; it is
created by ``Renderer.create_texture`` (or automatically when a sprite is
first drawn).  A :class:`TextureRegion` describes a rectangular part of an
image's texture, which is how sprite sheets and future animation select
cells.
"""

from __future__ import annotations

from ..backend.base import BackendTexture
from ..exceptions import ConfigurationError
from .image import Image


def _non_negative(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"{name} must be a non-negative integer, got {value!r}.")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer, got {value!r}.")
    return value


class Texture:
    """A drawable image prepared for a specific renderer.

    Created by ``Renderer.create_texture`` so it is bound to the backend
    renderer of whichever window is currently open.  Textures are freed by
    calling :meth:`destroy` or, automatically, when the renderer (and the
    window) is destroyed.
    """

    def __init__(self, backend_texture: BackendTexture) -> None:
        self._backend_texture = backend_texture
        self._destroyed = False

    @property
    def width(self) -> int:
        """The texture width in pixels."""
        self._check()
        return self._backend_texture.width

    @property
    def height(self) -> int:
        """The texture height in pixels."""
        self._check()
        return self._backend_texture.height

    def destroy(self) -> None:
        """Free the underlying texture.  Idempotent."""
        if self._destroyed:
            return
        self._backend_texture.destroy()
        self._destroyed = True

    def _check(self) -> None:
        if self._destroyed:
            raise RuntimeError("Cannot use a texture after it has been destroyed.")


class TextureRegion:
    """A rectangular region of an image, usable as a sprite source.

    Regions are cheap and renderer-independent: the underlying texture is
    resolved only when a sprite created from the region is drawn.
    """

    def __init__(
        self,
        image: Image,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        if not isinstance(image, Image):
            raise ConfigurationError("TextureRegion requires a pydex_ge.Image.")
        x = _non_negative(x, "x")
        y = _non_negative(y, "y")
        width = _positive(width, "width")
        height = _positive(height, "height")
        if x + width > image.width or y + height > image.height:
            raise ConfigurationError(
                f"Region ({x}, {y}, {width}, {height}) exceeds the image size "
                f"{image.width}x{image.height}."
            )
        self.image = image
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def sprite(self) -> Sprite:  # noqa: F821 - imported lazily below
        """Return a :class:`~pydex_ge.graphics.sprite.Sprite` for this region."""
        from .sprite import Sprite

        return Sprite(self.image, region=(self.x, self.y, self.width, self.height))


__all__ = ["Texture", "TextureRegion"]