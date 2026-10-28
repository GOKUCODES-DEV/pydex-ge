"""The :class:`Vector2`: a 2D float vector for geometry and movement.

Part 7 is a **math/geometry foundation**.  PYDEX vectors hold two numbers
(``x`` and ``y``), support the usual arithmetic, and provide the common
geometry helpers (length, normalize, dot, rotate, and so on).  They are
deliberately *not* a physics engine: there is no gravity, velocity
integration, or collision resolution here.

Vectors accept floats; integers are accepted and treated as their float
value.  ``bool`` is rejected (it is not a number) and raises a clear
:class:`~pydex_ge.exceptions.ConfigurationError`.
"""

from __future__ import annotations

import math

from ..exceptions import ConfigurationError

_EPSILON = 1e-9


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    return float(value)


class Vector2:
    """A 2D vector with float components.

    Parameters
    ----------
    x, y:
        The two components.  Default to ``0.0``.  Accepts floats or ints.
        A single value sets both components; a two-element tuple/list is
        unpacked into ``x`` and ``y``.
    """

    __slots__ = ("_x", "_y")

    def __init__(self, x: object = 0.0, y: object | None = None) -> None:
        if isinstance(x, (tuple, list)) and y is None:
            if len(x) != 2:
                raise ConfigurationError(
                    f"A vector built from an iterable needs exactly 2 values, "
                    f"got {len(x)}."
                )
            x, y = x[0], x[1]
        if y is None:
            y = x
        self._x = _number(x, "x")
        self._y = _number(y, "y")

    # -- components -------------------------------------------------------

    @property
    def x(self) -> float:
        """The horizontal component."""
        return self._x

    @x.setter
    def x(self, value: object) -> None:
        self._x = _number(value, "x")

    @property
    def y(self) -> float:
        """The vertical component."""
        return self._y

    @y.setter
    def y(self, value: object) -> None:
        self._y = _number(value, "y")

    # -- construction -----------------------------------------------------

    @classmethod
    def from_polar(cls, length: object, degrees: object) -> Vector2:
        """Build a vector of ``length`` pointing at ``degrees`` (0 = +X axis).

        Angles are measured clockwise from the positive X axis so the vector
        follows the PYDEX screen coordinate system where ``+Y`` points down.
        """
        length = _number(length, "length")
        degrees = _number(degrees, "degrees")
        if length < 0:
            raise ConfigurationError("length must be non-negative.")
        angle = math.radians(degrees)
        return cls(length * math.cos(angle), length * math.sin(angle))

    @classmethod
    def zero(cls) -> Vector2:
        """The zero vector ``(0.0, 0.0)``."""
        return cls(0.0, 0.0)

    # -- arithmetic -------------------------------------------------------

    def __add__(self, other: object) -> Vector2:
        if isinstance(other, Vector2):
            return Vector2(self.x + other.x, self.y + other.y)
        raise TypeError(f"Cannot add {other!r} to a Vector2.")

    def __sub__(self, other: object) -> Vector2:
        if isinstance(other, Vector2):
            return Vector2(self.x - other.x, self.y - other.y)
        raise TypeError(f"Cannot subtract {other!r} from a Vector2.")

    def __mul__(self, other: object) -> Vector2:
        if isinstance(other, Vector2):
            return Vector2(self.x * other.x, self.y * other.y)
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            raise TypeError(f"Cannot multiply a Vector2 by {other!r}.")
        return Vector2(self.x * float(other), self.y * float(other))

    def __rmul__(self, other: object) -> Vector2:
        return self.__mul__(other)

    def __truediv__(self, other: object) -> Vector2:
        if isinstance(other, Vector2):
            if other.x == 0 or other.y == 0:
                raise ZeroDivisionError("Cannot divide by a zero vector.")
            return Vector2(self.x / other.x, self.y / other.y)
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            raise TypeError(f"Cannot divide a Vector2 by {other!r}.")
        if float(other) == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return Vector2(self.x / float(other), self.y / float(other))

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __iadd__(self, other: object) -> Vector2:
        if not isinstance(other, Vector2):
            raise TypeError(f"Cannot add {other!r} to a Vector2.")
        self._x += other.x
        self._y += other.y
        return self

    def __isub__(self, other: object) -> Vector2:
        if not isinstance(other, Vector2):
            raise TypeError(f"Cannot subtract {other!r} from a Vector2.")
        self._x -= other.x
        self._y -= other.y
        return self

    def __imul__(self, other: object) -> Vector2:
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            raise TypeError(f"Cannot multiply a Vector2 by {other!r}.")
        self._x *= float(other)
        self._y *= float(other)
        return self

    def __itruediv__(self, other: object) -> Vector2:
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            raise TypeError(f"Cannot divide a Vector2 by {other!r}.")
        if float(other) == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        self._x /= float(other)
        self._y /= float(other)
        return self

    # -- sequence protocol -----------------------------------------------

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError("Vector2 index out of range (valid: 0 and 1).")

    def __iter__(self):
        yield self.x
        yield self.y

    def __bool__(self) -> bool:
        return self.x != 0.0 or self.y != 0.0

    # -- geometry ---------------------------------------------------------

    @property
    def length(self) -> float:
        """The magnitude of the vector."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    @property
    def length_squared(self) -> float:
        """The magnitude squared (cheaper to compute than :attr:`length`)."""
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vector2:
        """Return the vector scaled to unit length (length 1).

        The zero vector normalizes to itself.
        """
        length = self.length
        if length < _EPSILON:
            return Vector2(0.0, 0.0)
        return Vector2(self.x / length, self.y / length)

    def dot(self, other: object) -> float:
        """The dot product with ``other``."""
        if not isinstance(other, Vector2):
            raise TypeError(f"Cannot compute the dot product with {other!r}.")
        return self.x * other.x + self.y * other.y

    def cross(self, other: object) -> float:
        """The 2D (scalar) cross product with ``other``."""
        if not isinstance(other, Vector2):
            raise TypeError(f"Cannot compute the cross product with {other!r}.")
        return self.x * other.y - self.y * other.x

    def distance(self, other: object) -> float:
        """The Euclidean distance to ``other``."""
        if not isinstance(other, Vector2):
            raise TypeError(f"Cannot measure the distance to {other!r}.")
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def rotate(self, degrees: object) -> Vector2:
        """Return this vector rotated clockwise by ``degrees`` (screen coords).

        Consistent with :meth:`from_polar`: rotating by ``+90`` turns the
        ``+X`` vector into the ``+Y`` (down) vector.
        """
        degrees = _number(degrees, "degrees")
        angle = math.radians(degrees)
        cos = math.cos(angle)
        sin = math.sin(angle)
        return Vector2(
            self.x * cos - self.y * sin,
            self.x * sin + self.y * cos,
        )

    def perpendicular(self) -> Vector2:
        """Return a vector perpendicular to this one (``rotate(90)``)."""
        return Vector2(-self.y, self.x)

    def clamp_length(self, maximum: object) -> Vector2:
        """Return this vector limited to ``maximum`` length (or itself if shorter)."""
        maximum = _number(maximum, "maximum")
        if maximum < 0:
            raise ConfigurationError("maximum must be non-negative.")
        length = self.length
        if length <= maximum or length < _EPSILON:
            return Vector2(self.x, self.y)
        scale = maximum / length
        return Vector2(self.x * scale, self.y * scale)

    def copy(self) -> Vector2:
        """A new vector with the same components."""
        return Vector2(self.x, self.y)

    # -- protocol ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return (
            abs(self.x - other.x) < _EPSILON
            and abs(self.y - other.y) < _EPSILON
        )

    def __hash__(self) -> int:
        # Vectors are mutable, so equality-hash them by rounded values so a
        # mutated vector no longer matches its old key.  This keeps them
        # usable as dict keys without silent surprises.
        #
        # The grid must be coarser than the _EPSILON used by __eq__ so that
        # two tolerance-equal vectors land in the same bucket.  round(x, 8)
        # (a 1e-8 grid, 10x the 1e-9 tolerance) does that; round(x, 9) is
        # exactly the tolerance width, so equal vectors often hash apart.
        return hash((round(self.x, 8), round(self.y, 8)))

    def __repr__(self) -> str:
        return f"Vector2({self.x!r}, {self.y!r})"


__all__ = ["Vector2"]
