"""Core engine abstractions: the game object, window, clock, and events."""

from __future__ import annotations

from ..backend import select_backend
from ..backend.base import Backend, BackendRenderer, BackendWindow
from ..exceptions import ConfigurationError
from .renderer import Renderer


def _validate_size(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer, got {value!r}.")
    return value


class Window:
    """An abstract window with a title and size.

    The window is created lazily: nothing appears on screen until
    :meth:`open` is called, and the concrete backend window stays hidden
    behind this class.  Callers never touch SDL objects directly.

    Parameters
    ----------
    title:
        Title shown in the window title bar.
    width, height:
        Window size in pixels; must be positive integers.
    backend:
        Backend used to create the native window.  Defaults to SDL2 (or
        the ``PYDEX_BACKEND`` environment variable).
    """

    def __init__(
        self,
        title: str = "PYDEX",
        width: int = 800,
        height: int = 600,
        *,
        backend: Backend | None = None,
    ) -> None:
        if not isinstance(title, str) or not title.strip():
            raise ConfigurationError("Window title must be a non-empty string.")
        self._title = title
        self._width = _validate_size(width, "width")
        self._height = _validate_size(height, "height")
        self._backend = backend if backend is not None else select_backend()
        self._backend_window: BackendWindow | None = None
        self._renderer: Renderer | None = None
        self._closed = True

    def open(self) -> None:
        """Create (and show) the native window.  No-op if already open."""
        if not self._closed:
            return
        self._backend.init()
        self._backend_window = self._backend.create_window(
            self._title, self._width, self._height
        )
        self._closed = False

    def close(self) -> None:
        """Destroy the renderer and native window, if any.  Idempotent."""
        if self._closed:
            return
        if self._renderer is not None:
            self._renderer.destroy()
            self._renderer = None
        if self._backend_window is not None:
            self._backend_window.close()
            self._backend_window = None
        self._closed = True

    def resize(self, width: int, height: int) -> None:
        """Update the logical window size (e.g. after a resize event)."""
        self._width = _validate_size(width, "width")
        self._height = _validate_size(height, "height")
        if self._renderer is not None:
            self._renderer._set_size((self._width, self._height))

    @property
    def closed(self) -> bool:
        """True when no native window currently exists."""
        return self._closed

    @property
    def title(self) -> str:
        """The window title."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError("Window title must be a non-empty string.")
        self._title = value

    @property
    def width(self) -> int:
        """The window width in pixels (fixed after construction)."""
        return self._width

    @property
    def height(self) -> int:
        """The window height in pixels (fixed after construction)."""
        return self._height

    @property
    def renderer(self) -> Renderer:
        """The window renderer, created lazily.

        Only available while the window is open; accessing it on a closed
        window raises :class:`RuntimeError`.
        """
        if self._closed:
            raise RuntimeError("Window renderer is only available while the window is open.")
        if self._renderer is None:
            backend_renderer: BackendRenderer = self._backend.create_renderer(
                self._backend_window
            )
            self._renderer = Renderer(backend_renderer, size=(self._width, self._height))
        return self._renderer


__all__ = ["Window"]