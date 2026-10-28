"""2D drawing commands for PYDEX.

Coordinates use the PYDEX coordinate system:

::

    (0, 0) ────────────→ X (right)
      │
      │
      ↓
      Y (down)

The origin is the top-left corner of the window and coordinates are
measured in pixels.  There is no camera or world-coordinate transform
yet.
"""
from __future__ import annotations

from ..backend.base import BackendRenderer
from ..exceptions import ConfigurationError
from .color import normalize_rgba

_DEFAULT_COLOR = (255, 255, 255)


def _coord(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer, got {value!r}.")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer, got {value!r}.")
    return value


class DrawCommands:
    """A namespace of 2D drawing commands for a window renderer.

    ``color`` is an RGB or RGBA tuple with each channel an int in 0-255.
    Rectangles and circles are filled by default; pass ``filled=False``
    to draw just the outline.
    """

    def __init__(self, renderer: BackendRenderer) -> None:
        self._renderer = renderer

    def pixel(
        self, x: int, y: int, color: tuple[int, int, int] = _DEFAULT_COLOR
    ) -> None:
        """Draw a single pixel at ``(x, y)``."""
        self._renderer.draw_pixel(
            _coord(x, "x"), _coord(y, "y"), normalize_rgba(color)
        )

    def line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple[int, int, int] = _DEFAULT_COLOR,
    ) -> None:
        """Draw a line between ``(x1, y1)`` and ``(x2, y2)``."""
        self._renderer.draw_line(
            _coord(x1, "x1"),
            _coord(y1, "y1"),
            _coord(x2, "x2"),
            _coord(y2, "y2"),
            normalize_rgba(color),
        )

    def rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int] = _DEFAULT_COLOR,
        filled: bool = True,
    ) -> None:
        """Draw a rectangle at ``(x, y)`` with the given size."""
        self._renderer.draw_rect(
            _coord(x, "x"),
            _coord(y, "y"),
            _positive(width, "width"),
            _positive(height, "height"),
            normalize_rgba(color),
            filled=filled,
        )

    def circle(
        self,
        x: int,
        y: int,
        radius: int,
        color: tuple[int, int, int] = _DEFAULT_COLOR,
        filled: bool = True,
    ) -> None:
        """Draw a circle centered at ``(x, y)`` with the given radius."""
        self._renderer.draw_circle(
            _coord(x, "x"),
            _coord(y, "y"),
            _positive(radius, "radius"),
            normalize_rgba(color),
            filled=filled,
        )


__all__ = ["DrawCommands"]