"""The :class:`Quaternion`: a compact rotation representation for 3D.

Part 3D builds a small CPU-side 3D subsystem.  A quaternion stores a
rotation as four numbers (``w``, ``x``, ``y``, ``z``) and avoids the
gimbal-lock and interpolation problems of raw angles.  PYDEX uses
unit quaternions for camera and object orientation.

Euler angles are always **degrees** in the public API (beginner-friendly),
but all composition happens with quaternion multiplication so there is no
drift.

Quaternions accept floats; integers are accepted and treated as their float
value.  ``bool`` is rejected and raises a clear
:class:`~pydex_ge.exceptions.ConfigurationError`.
"""

from __future__ import annotations

import math

from ..exceptions import ConfigurationError
from ..physics.vector3 import Vector3

_EPSILON = 1e-9


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    return float(value)


class Quaternion:
    """A unit quaternion representing a 3D rotation.

    Parameters
    ----------
    w, x, y, z:
        The four components.  Defaults build the identity rotation.
        Accepts floats or ints.
    """

    __slots__ = ("_w", "_x", "_y", "_z")

    def __init__(self, w: object = 1.0, x: object = 0.0, y: object = 0.0, z: object = 0.0) -> None:
        self._w = _number(w, "w")
        self._x = _number(x, "x")
        self._y = _number(y, "y")
        self._z = _number(z, "z")

    # -- components -------------------------------------------------------

    @property
    def w(self) -> float:
        """The scalar component."""
        return self._w

    @w.setter
    def w(self, value: object) -> None:
        self._w = _number(value, "w")

    @property
    def x(self) -> float:
        """The i component."""
        return self._x

    @x.setter
    def x(self, value: object) -> None:
        self._x = _number(value, "x")

    @property
    def y(self) -> float:
        """The j component."""
        return self._y

    @y.setter
    def y(self, value: object) -> None:
        self._y = _number(value, "y")

    @property
    def z(self) -> float:
        """The k component."""
        return self._z

    @z.setter
    def z(self, value: object) -> None:
        self._z = _number(value, "z")

    # -- construction -----------------------------------------------------

    @classmethod
    def identity(cls) -> Quaternion:
        """The identity rotation ``(1.0, 0.0, 0.0, 0.0)``."""
        return cls(1.0, 0.0, 0.0, 0.0)

    @classmethod
    def from_axis_angle(cls, axis: object, degrees: object) -> Quaternion:
        """Build a rotation of ``degrees`` about the given ``axis``.

        Parameters
        ----------
        axis:
            A :class:`Vector3` (or 3-tuple) axis.  Must be non-zero.
        degrees:
            Rotation amount in degrees.
        """
        degrees = _number(degrees, "degrees")
        if isinstance(axis, (tuple, list)):
            axis = Vector3(axis)
        if not isinstance(axis, Vector3):
            raise ConfigurationError(
                f"axis must be a Vector3 or 3-tuple, got {axis!r}."
            )
        length = axis.length
        if length < _EPSILON:
            raise ConfigurationError("axis must be non-zero.")
        half = math.radians(degrees) / 2.0
        sin = math.sin(half)
        return cls(
            math.cos(half),
            axis.x / length * sin,
            axis.y / length * sin,
            axis.z / length * sin,
        )

    @classmethod
    def from_euler(cls, yaw: object, pitch: object, roll: object) -> Quaternion:
        """Build a rotation from ``yaw``, ``pitch`` and ``roll`` (degrees).

        The composite rotation applies roll about Z, then pitch about X,
        then yaw about Y.  ``yaw`` is a rotation around the vertical axis,
        which makes it the natural "turn the camera left/right" control.
        """
        yaw = _number(yaw, "yaw")
        pitch = _number(pitch, "pitch")
        roll = _number(roll, "roll")
        cy = math.cos(math.radians(yaw) / 2.0)
        sy = math.sin(math.radians(yaw) / 2.0)
        cp = math.cos(math.radians(pitch) / 2.0)
        sp = math.sin(math.radians(pitch) / 2.0)
        cr = math.cos(math.radians(roll) / 2.0)
        sr = math.sin(math.radians(roll) / 2.0)
        q_yaw = cls(cy, 0.0, sy, 0.0)
        q_pitch = cls(cp, sp, 0.0, 0.0)
        q_roll = cls(cr, 0.0, 0.0, sr)
        return q_yaw * q_pitch * q_roll

    # -- geometry ---------------------------------------------------------

    @property
    def length(self) -> float:
        """The magnitude of the quaternion (1.0 for a unit quaternion)."""
        return math.sqrt(self._w * self._w + self._x * self._x + self._y * self._y + self._z * self._z)

    @property
    def length_squared(self) -> float:
        """The magnitude squared."""
        return self._w * self._w + self._x * self._x + self._y * self._y + self._z * self._z

    def normalized(self) -> Quaternion:
        """Return the unit-length quaternion (or identity if zero)."""
        length = self.length
        if length < _EPSILON:
            return Quaternion.identity()
        return Quaternion(self.w / length, self.x / length, self.y / length, self.z / length)

    def conjugate(self) -> Quaternion:
        """Return the conjugate ``(w, -x, -y, -z)`` (the inverse of a unit quaternion)."""
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def inverse(self) -> Quaternion:
        """Return the multiplicative inverse.

        For a unit quaternion this equals the conjugate.  A zero quaternion
        has no inverse and returns the identity instead.
        """
        norm2 = self.length_squared
        if norm2 < _EPSILON:
            return Quaternion.identity()
        inv = 1.0 / norm2
        return Quaternion(self.w * inv, -self.x * inv, -self.y * inv, -self.z * inv)

    def to_euler(self) -> tuple[float, float, float]:
        """Return ``(yaw, pitch, roll)`` in degrees.

        The inverse of :meth:`from_euler` using the same apply-order
        (roll about Z, then pitch about X, then yaw about Y).
        """
        w, x, y, z = self.w, self.x, self.y, self.z
        yaw = math.atan2(2.0 * (x * z + w * y), 1.0 - 2.0 * (y * y + x * x))
        pitch_sin = 2.0 * (w * x - y * z)
        pitch_sin = max(-1.0, min(1.0, pitch_sin))
        pitch = math.asin(pitch_sin)
        roll = math.atan2(2.0 * (x * y + w * z), 1.0 - 2.0 * (x * x + z * z))
        return (
            math.degrees(yaw),
            math.degrees(pitch),
            math.degrees(roll),
        )

    def rotate_vector(self, vector: object) -> Vector3:
        """Return ``vector`` rotated by this quaternion.

        ``vector`` may be a :class:`Vector3` or a 3-tuple/list.
        """
        if isinstance(vector, (tuple, list)):
            vector = Vector3(vector)
        if not isinstance(vector, Vector3):
            raise ConfigurationError(
                f"vector must be a Vector3 or 3-tuple, got {vector!r}."
            )
        q = self.normalized()
        u = Vector3(q.x, q.y, q.z)
        s = q.w
        # Rodrigues' rotation formula: v' = v + 2*s*(u x v) + 2*(u x (u x v))
        u_cross_v = u.cross(vector)
        u_cross_u_cross_v = u.cross(u_cross_v)
        return vector + u_cross_v * (2.0 * s) + u_cross_u_cross_v * 2.0

    def copy(self) -> Quaternion:
        """A new quaternion with the same components."""
        return Quaternion(self.w, self.x, self.y, self.z)

    # -- arithmetic -------------------------------------------------------

    def __mul__(self, other: object) -> Quaternion:
        """Hamilton (quaternion) product, used to compose rotations.

        ``a * b`` means "rotate by ``b`` first, then by ``a``".
        """
        if not isinstance(other, Quaternion):
            raise TypeError(f"Cannot multiply a Quaternion by {other!r}.")
        a_w, a_x, a_y, a_z = self.w, self.x, self.y, self.z
        b_w, b_x, b_y, b_z = other.w, other.x, other.y, other.z
        return Quaternion(
            a_w * b_w - a_x * b_x - a_y * b_y - a_z * b_z,
            a_w * b_x + a_x * b_w + a_y * b_z - a_z * b_y,
            a_w * b_y - a_x * b_z + a_y * b_w + a_z * b_x,
            a_w * b_z + a_x * b_y - a_y * b_x + a_z * b_w,
        )

    # -- protocol ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quaternion):
            return NotImplemented
        return (
            abs(self.w - other.w) < _EPSILON
            and abs(self.x - other.x) < _EPSILON
            and abs(self.y - other.y) < _EPSILON
            and abs(self.z - other.z) < _EPSILON
        )

    def __hash__(self) -> int:
        # Same rule as Vector2/Vector3 and Rect: the hash grid must be
        # coarser than the _EPSILON used by __eq__ so two tolerance-equal
        # quaternions land in the same bucket.  round(x, 8) (a 1e-8 grid,
        # 10x the 1e-9 tolerance) does that; round(x, 9) is exactly the
        # tolerance width, so equal quaternions often hash apart.
        return hash((round(self.w, 8), round(self.x, 8), round(self.y, 8), round(self.z, 8)))

    def __repr__(self) -> str:
        return f"Quaternion({self.w!r}, {self.x!r}, {self.y!r}, {self.z!r})"


__all__ = ["Quaternion"]
