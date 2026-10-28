"""The :class:`Image` object: a decoded image file, ready for sprites."""

from __future__ import annotations

from ..backend import select_backend
from ..backend.base import Backend, BackendImage
from ..check import _caller_info
from ..exceptions import ConfigurationError, MissingAssetError


class Image:
    """A loaded image file (PNG/JPG/BMP) that sprites can draw from.

    An :class:`Image` holds the decoded image; it becomes drawable only
    when a renderer converts it into a :class:`~pydex_ge.graphics.texture.Texture`.
    Both ``pydex_ge.Image`` and ``pydex_ge.Sprite`` accept the same file formats.

    Parameters
    ----------
    path:
        Filesystem path to an image file.
    backend:
        Backend used to decode the image.  Defaults to SDL2 (or the
        ``PYDEX_BACKEND`` environment variable), matching the window.
    """

    def __init__(self, path: str, *, backend: Backend | None = None) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ConfigurationError("Image path must be a non-empty string.")
        self.path = path
        self._backend = backend if backend is not None else select_backend()
        try:
            self._image: BackendImage = self._backend.load_image(path)
        except MissingAssetError as exc:
            if exc.requested_by is None:
                exc.requested_by = _caller_info()
            raise
        self._destroyed = False

    @property
    def width(self) -> int:
        """The image width in pixels."""
        self._check()
        return self._image.width

    @property
    def height(self) -> int:
        """The image height in pixels."""
        self._check()
        return self._image.height

    def destroy(self) -> None:
        """Free the decoded image.  Idempotent."""
        if self._destroyed:
            return
        self._image.destroy()
        self._destroyed = True

    def _check(self) -> None:
        if self._destroyed:
            raise RuntimeError("Cannot use an image after it has been destroyed.")

    @property
    def _backend_image(self) -> BackendImage:
        self._check()
        return self._image

    @classmethod
    def _from_backend_image(
        cls, backend_image: BackendImage, *, backend: Backend
    ) -> Image:
        """Wrap an already-loaded backend image (e.g. rendered text)."""
        image = cls.__new__(cls)
        image.path = "<rendered>"
        image._backend = backend
        image._image = backend_image
        image._destroyed = False
        return image


__all__ = ["Image"]