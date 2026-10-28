"""The :class:`Rect`: an axis-aligned rectangle for geometry and collision.

A :class:`Rect` is defined by its top-left corner ``(x, y)`` and its
``width``/``height``.  Coordinates and sizes accept floats.  A rectangle
with zero width or height is allowed (it occupies no area); predicates
treat such degenerate rectangles consistently without ever dividing by
zero.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .vector import Vector2

_EPSILON = 1e-9


def _number(value: object, name: str, *, non_negative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if non_negative and number < 0:
        raise ConfigurationError(f"{name} must be non-negative, got {value!r}.")
    return number


def _as_vector(value: object, name: str) -> Vector2:
    if isinstance(value, Vector2):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Vector2(value[0], value[1])
    raise ConfigurationError(
        f"{name} must be a Vector2 or a 2-element (x, y) sequence, got {value!r}."
    )


class Rect:
    """An axis-aligned rectangle.

    Parameters
    ----------
    x, y, width, height:
        Top-left corner and size.  ``x``/``y``/``width``/``height`` default
        to ``0.0``.  ``width`` and ``height`` must be non-negative.
    position:
        Alternative to ``x, y``: a :class:`~pydex_ge.physics.Vector2` or a
        ``(x, y)`` sequence.
    size:
        Alternative to ``width, height``: a :class:`~pydex_ge.physics.Vector2`
        or a ``(width, height)`` sequence.
    """

    __slots__ = ("_x", "_y", "_width", "_height")

    def __init__(
        self,
        x: object = 0.0,
        y: object = 0.0,
        width: object = 0.0,
        height: object = 0.0,
        *,
        position=None,
        size=None,
    ) -> None:
        if position is not None:
            position = _as_vector(position, "position")
            x, y = position.x, position.y
        if size is not None:
            size = _as_vector(size, "size")
            width, height = size.x, size.y
        self._x = _number(x, "x")
        self._y = _number(y, "y")
        self._width = _number(width, "width", non_negative=True)
        self._height = _number(height, "height", non_negative=True)

    # -- components -------------------------------------------------------

    @property
    def x(self) -> float:
        """The left edge (the ``x`` of the top-left corner)."""
        return self._x

    @x.setter
    def x(self, value: object) -> None:
        self._x = _number(value, "x")

    @property
    def y(self) -> float:
        """The top edge (the ``y`` of the top-left corner)."""
        return self._y

    @y.setter
    def y(self, value: object) -> None:
        self._y = _number(value, "y")

    @property
    def width(self) -> float:
        """The rectangle width."""
        return self._width

    @width.setter
    def width(self, value: object) -> None:
        self._width = _number(value, "width", non_negative=True)

    @property
    def height(self) -> float:
        """The rectangle height."""
        return self._height

    @height.setter
    def height(self, value: object) -> None:
        self._height = _number(value, "height", non_negative=True)

    # -- derived edges ----------------------------------------------------

    @property
    def left(self) -> float:
        """The left edge (same as :attr:`x`)."""
        return self._x

    @property
    def right(self) -> float:
        """The right edge (``x + width``)."""
        return self._x + self._width

    @property
    def top(self) -> float:
        """The top edge (same as :attr:`y`)."""
        return self._y

    @property
    def bottom(self) -> float:
        """The bottom edge (``y + height``)."""
        return self._y + self._height

    @property
    def center(self) -> Vector2:
        """The center point as a :class:`~pydex_ge.physics.Vector2`."""
        return Vector2(self._x + self._width / 2, self._y + self._height / 2)

    @property
    def top_left(self) -> Vector2:
        """The top-left corner ``(x, y)``."""
        return Vector2(self._x, self._y)

    @property
    def top_right(self) -> Vector2:
        """The top-right corner ``(x + width, y)``."""
        return Vector2(self._x + self._width, self._y)

    @property
    def bottom_left(self) -> Vector2:
        """The bottom-left corner ``(x, y + height)``."""
        return Vector2(self._x, self._y + self._height)

    @property
    def bottom_right(self) -> Vector2:
        """The bottom-right corner ``(x + width, y + height)``."""
        return Vector2(self._x + self._width, self._y + self._height)

    @property
    def size(self) -> Vector2:
        """The size ``(width, height)`` as a :class:`~pydex_ge.physics.Vector2`."""
        return Vector2(self._width, self._height)

    # -- geometry ---------------------------------------------------------

    def contains_point(self, point: object) -> bool:
        """True when ``point`` lies on or inside the rectangle."""
        point = _as_vector(point, "point")
        return (
            self._x <= point.x <= self._x + self._width
            and self._y <= point.y <= self._y + self._height
        )

    def overlaps(self, other: object) -> bool:
        """True when this rectangle overlaps ``other`` (touching edges count)."""
        other = _as_rect(other, "other")
        return (
            self._x <= other.x + other.width
            and other.x <= self._x + self._width
            and self._y <= other.y + other.height
            and other.y <= self._y + self._height
        )

    def contains(self, other: object) -> bool:
        """True when ``other`` is fully inside this rectangle (edges may touch)."""
        other = _as_rect(other, "other")
        return (
            other.x >= self._x
            and other.y >= self._y
            and other.x + other.width <= self._x + self._width
            and other.y + other.height <= self._y + self._height
        )

    def intersection(self, other: object) -> Rect | None:
        """The overlap region with ``other``, or ``None`` if they do not overlap."""
        other = _as_rect(other, "other")
        left = max(self._x, other.x)
        top = max(self._y, other.y)
        right = min(self._x + self._width, other.x + other.width)
        bottom = min(self._y + self._height, other.y + other.height)
        if right < left or bottom < top:
            return None
        return Rect(left, top, right - left, bottom - top)

    def union(self, other: object) -> Rect:
        """The smallest rectangle that contains both this and ``other``."""
        other = _as_rect(other, "other")
        left = min(self._x, other.x)
        top = min(self._y, other.y)
        right = max(self._x + self._width, other.x + other.width)
        bottom = max(self._y + self._height, other.y + other.height)
        return Rect(left, top, right - left, bottom - top)

    def inflate(self, dx: object, dy: object) -> Rect:
        """Return a copy grown by ``dx`` on each side and ``dy`` on top/bottom."""
        dx = _number(dx, "dx")
        dy = _number(dy, "dy")
        width = self._width + 2 * dx
        height = self._height + 2 * dy
        if width < 0 or height < 0:
            raise ConfigurationError(
                "inflate would make the rectangle smaller than zero size."
            )
        return Rect(self._x - dx, self._y - dy, width, height)

    def moved(self, dx: object, dy: object) -> Rect:
        """Return a copy shifted by ``dx``, ``dy`` (without changing size)."""
        dx = _number(dx, "dx")
        dy = _number(dy, "dy")
        return Rect(self._x + dx, self._y + dy, self._width, self._height)

    def move(self, dx: object, dy: object) -> None:
        """Shift this rectangle in place by ``dx``, ``dy``."""
        dx = _number(dx, "dx")
        dy = _number(dy, "dy")
        self._x += dx
        self._y += dy

    def copy(self) -> Rect:
        """A new rectangle with the same geometry."""
        return Rect(self._x, self._y, self._width, self._height)

    # -- protocol ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rect):
            return NotImplemented
        return (
            abs(self._x - other._x) < _EPSILON
            and abs(self._y - other._y) < _EPSILON
            and abs(self._width - other._width) < _EPSILON
            and abs(self._height - other._height) < _EPSILON
        )

    def __hash__(self) -> int:
        # Same rule as Vector2/Vector3: the hash grid must be coarser than
        # _EPSILON so two tolerance-equal rects land in the same bucket.
        # round(x, 8) (a 1e-8 grid, 10x the 1e-9 tolerance) does that;
        # round(x, 9) is exactly the tolerance width, so equal rects often
        # hash apart.  See pydex_ge/physics/vector.py:__hash__.
        return hash(
            (
                round(self._x, 8),
                round(self._y, 8),
                round(self._width, 8),
                round(self._height, 8),
            )
        )

    def __repr__(self) -> str:
        return (
            f"Rect({self._x!r}, {self._y!r}, "
            f"{self._width!r}, {self._height!r})"
        )


def _as_rect(value: object, name: str) -> Rect:
    if isinstance(value, Rect):
        return value
    raise ConfigurationError(f"{name} must be a Rect, got {value!r}.")


__all__ = ["Rect"]
