"""The :class:`Vector3`: a 3D float vector for the 3D Foundation.

Part 3D builds a small CPU-side 3D subsystem on top of the existing 2D
engine.  :class:`Vector3` mirrors the conventions of :class:`Vector2`
exactly: it holds three floats (``x``, ``y`` and ``z``), supports the
usual arithmetic, and provides the common geometry helpers (length,
normalize, dot, cross, distance, and so on).

Like every PYDEX vector it is *not* a physics engine: there is no
gravity, velocity integration, or collision resolution here.

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


class Vector3:
    """A 3D vector with float components.

    Parameters
    ----------
    x, y, z:
        The three components.  Default to ``0.0``.  Accepts floats or ints.
        A single value sets all three components; a three-element
        tuple/list is unpacked into ``x``, ``y`` and ``z``.
    """

    __slots__ = ("_x", "_y", "_z")

    def __init__(self, x: object = 0.0, y: object | None = None, z: object | None = None) -> None:
        if isinstance(x, (tuple, list)) and y is None and z is None:
            if len(x) != 3:
                raise ConfigurationError(
                    f"A vector built from an iterable needs exactly 3 values, "
                    f"got {len(x)}."
                )
            x, y, z = x[0], x[1], x[2]
        if y is None:
            y = x
        if z is None:
            z = x
        self._x = _number(x, "x")
        self._y = _number(y, "y")
        self._z = _number(z, "z")

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

    @property
    def z(self) -> float:
        """The depth component."""
        return self._z

    @z.setter
    def z(self, value: object) -> None:
        self._z = _number(value, "z")

    # -- construction -----------------------------------------------------

    @classmethod
    def zero(cls) -> Vector3:
        """The zero vector ``(0.0, 0.0, 0.0)``."""
        return cls(0.0, 0.0, 0.0)

    @classmethod
    def one(cls) -> Vector3:
        """The one vector ``(1.0, 1.0, 1.0)``."""
        return cls(1.0, 1.0, 1.0)

    @classmethod
    def right(cls) -> Vector3:
        """The +X axis ``(1.0, 0.0, 0.0)``."""
        return cls(1.0, 0.0, 0.0)

    @classmethod
    def up(cls) -> Vector3:
        """The +Y axis ``(0.0, 1.0, 0.0)``."""
        return cls(0.0, 1.0, 0.0)

    @classmethod
    def forward(cls) -> Vector3:
        """The +Z axis ``(0.0, 0.0, 1.0)``."""
        return cls(0.0, 0.0, 1.0)

    # -- arithmetic -------------------------------------------------------

    def __add__(self, other: object) -> Vector3:
        if isinstance(other, Vector3):
            return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
        raise TypeError(f"Cannot add {other!r} to a Vector3.")

    def __sub__(self, other: object) -> Vector3:
        if isinstance(other, Vector3):
            return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
        raise TypeError(f"Cannot subtract {other!r} from a Vector3.")

    def __mul__(self, other: object) -> Vector3:
        if isinstance(other, Vector3):
            return Vector3(self.x * other.x, self.y * other.y, self.z * other.z)
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            raise TypeError(f"Cannot multiply a Vector3 by {other!r}.")
        return Vector3(self.x * float(other), self.y * float(other), self.z * float(other))

    def __rmul__(self, other: object) -> Vector3:
        return self.__mul__(other)

    def __truediv__(self, other: object) -> Vector3:
        if isinstance(other, Vector3):
            if other.x == 0 or other.y == 0 or other.z == 0:
                raise ZeroDivisionError("Cannot divide by a zero vector.")
            return Vector3(self.x / other.x, self.y / other.y, self.z / other.z)
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            raise TypeError(f"Cannot divide a Vector3 by {other!r}.")
        if float(other) == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return Vector3(self.x / float(other), self.y / float(other), self.z / float(other))

    def __neg__(self) -> Vector3:
        return Vector3(-self.x, -self.y, -self.z)

    def __iadd__(self, other: object) -> Vector3:
        if not isinstance(other, Vector3):
            raise TypeError(f"Cannot add {other!r} to a Vector3.")
        self._x += other.x
        self._y += other.y
        self._z += other.z
        return self

    def __isub__(self, other: object) -> Vector3:
        if not isinstance(other, Vector3):
            raise TypeError(f"Cannot subtract {other!r} from a Vector3.")
        self._x -= other.x
        self._y -= other.y
        self._z -= other.z
        return self

    def __imul__(self, other: object) -> Vector3:
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            raise TypeError(f"Cannot multiply a Vector3 by {other!r}.")
        self._x *= float(other)
        self._y *= float(other)
        self._z *= float(other)
        return self

    def __itruediv__(self, other: object) -> Vector3:
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            raise TypeError(f"Cannot divide a Vector3 by {other!r}.")
        if float(other) == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        self._x /= float(other)
        self._y /= float(other)
        self._z /= float(other)
        return self

    # -- sequence protocol -----------------------------------------------

    def __len__(self) -> int:
        return 3

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        if index == 2:
            return self.z
        raise IndexError("Vector3 index out of range (valid: 0, 1 and 2).")

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __bool__(self) -> bool:
        return self.x != 0.0 or self.y != 0.0 or self.z != 0.0

    # -- geometry ---------------------------------------------------------

    @property
    def length(self) -> float:
        """The magnitude of the vector."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    @property
    def length_squared(self) -> float:
        """The magnitude squared (cheaper to compute than :attr:`length`)."""
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalized(self) -> Vector3:
        """Return the vector scaled to unit length (length 1).

        The zero vector normalizes to itself.
        """
        length = self.length
        if length < _EPSILON:
            return Vector3(0.0, 0.0, 0.0)
        return Vector3(self.x / length, self.y / length, self.z / length)

    def dot(self, other: object) -> float:
        """The dot product with ``other``."""
        if not isinstance(other, Vector3):
            raise TypeError(f"Cannot compute the dot product with {other!r}.")
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: object) -> Vector3:
        """The 3D (vector) cross product with ``other``."""
        if not isinstance(other, Vector3):
            raise TypeError(f"Cannot compute the cross product with {other!r}.")
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def distance(self, other: object) -> float:
        """The Euclidean distance to ``other``."""
        if not isinstance(other, Vector3):
            raise TypeError(f"Cannot measure the distance to {other!r}.")
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def angle_between(self, other: object) -> float:
        """The angle (in degrees) between this vector and ``other``."""
        if not isinstance(other, Vector3):
            raise TypeError(f"Cannot measure the angle to {other!r}.")
        lengths = self.length * other.length
        if lengths < _EPSILON:
            return 0.0
        cosine = (self.dot(other) / lengths)
        cosine = max(-1.0, min(1.0, cosine))
        return math.degrees(math.acos(cosine))

    def clamp_length(self, maximum: object) -> Vector3:
        """Return this vector limited to ``maximum`` length (or itself if shorter)."""
        maximum = _number(maximum, "maximum")
        if maximum < 0:
            raise ConfigurationError("maximum must be non-negative.")
        length = self.length
        if length <= maximum or length < _EPSILON:
            return Vector3(self.x, self.y, self.z)
        scale = maximum / length
        return Vector3(self.x * scale, self.y * scale, self.z * scale)

    def copy(self) -> Vector3:
        """A new vector with the same components."""
        return Vector3(self.x, self.y, self.z)

    # -- protocol ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3):
            return NotImplemented
        return (
            abs(self.x - other.x) < _EPSILON
            and abs(self.y - other.y) < _EPSILON
            and abs(self.z - other.z) < _EPSILON
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
        return hash((round(self.x, 8), round(self.y, 8), round(self.z, 8)))

    def __repr__(self) -> str:
        return f"Vector3({self.x!r}, {self.y!r}, {self.z!r})"


__all__ = ["Vector3"]
