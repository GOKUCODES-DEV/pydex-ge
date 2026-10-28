"""The :class:`Transform3D`: a reusable 3D transformation object.

Part 3D builds a small CPU-side 3D subsystem.  A transform holds a
:class:`~pydex_ge.physics.vector3.Vector3` position, a
:class:`~pydex_ge.math.quaternion.Quaternion` rotation, a per-axis scale,
an origin (local pivot) and an optional parent.  Child transforms inherit
their parent's movement:

* world position = parent world position + parent rotation applied to
  (parent scale * local position),
* world rotation = parent world rotation * local rotation (quaternion
  product),
* world scale = component-wise multiplication of the two scales.

This mirrors the :class:`~pydex_ge.transform.Transform2D` conventions, with
rotation stored as a quaternion instead of degrees.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from ..math.quaternion import Quaternion
from ..physics.vector3 import Vector3

_EPSILON = 1e-9


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    return float(value)


def _as_vector(value: object, name: str) -> Vector3:
    if isinstance(value, Vector3):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return Vector3(value[0], value[1], value[2])
    raise ConfigurationError(
        f"{name} must be a Vector3 or a 3-element (x, y, z) sequence, got {value!r}."
    )


def _as_quaternion(value: object, name: str) -> Quaternion:
    if isinstance(value, Quaternion):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 4:
        return Quaternion(value[0], value[1], value[2], value[3])
    raise ConfigurationError(
        f"{name} must be a Quaternion or a 4-element (w, x, y, z) sequence, got {value!r}."
    )


def _as_scale(value: object) -> Vector3:
    """Normalize a scale value (a number or an ``(x, y, z)`` triple) to a Vector3."""
    if isinstance(value, (tuple, list)):
        if len(value) != 3:
            raise ConfigurationError(
                f"scale must be a number or a 3-element (x, y, z) triple, got {value!r}."
            )
        sx, sy, sz = value[0], value[1], value[2]
    elif isinstance(value, Vector3):
        sx, sy, sz = value.x, value.y, value.z
    else:
        sx = sy = sz = value
    return Vector3(
        _scale(sx, "scale"),
        _scale(sy, "scale"),
        _scale(sz, "scale"),
    )


def _scale(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number greater than zero, got {value!r}.")
    number = float(value)
    if number <= 0:
        raise ConfigurationError(f"{name} must be a number greater than zero, got {value!r}.")
    return number


class Transform3D:
    """A position, rotation, scale, and origin with optional parent/child links.

    Parameters
    ----------
    position:
        The local ``(x, y, z)`` position (a :class:`~pydex_ge.physics.Vector3`
        or an ``(x, y, z)`` triple).  Defaults to ``(0, 0, 0)``.
    rotation:
        The local rotation as a :class:`~pydex_ge.math.Quaternion` (or a
        ``(w, x, y, z)`` sequence).  Defaults to identity.
    scale:
        A uniform scale ``2`` or a per-axis ``(2, 1, 0.5)`` triple.  Each
        axis must be greater than zero.  Defaults to ``1``.
    origin:
        A local pivot ``(x, y, z)`` offset in object units.  Defaults to
        ``(0, 0, 0)``.  Used by :class:`~pydex_ge.graphics.Object3D` to rotate
        a mesh about a point other than the transform's own position.
    parent:
        An optional parent :class:`Transform3D`.

    Example
    -------
    ::

        ship = pydex_ge.Transform3D(position=(0, 0, -5), rotation=pydex_ge.Quaternion.from_euler(0, 45, 0))
        gun = pydex_ge.Transform3D(position=(1, 0, 0), parent=ship)
        ship.position = (0, 0, -10)     # gun follows automatically

    Values are validated; ``bool`` is rejected (it is not a number).
    """

    def __init__(
        self,
        *,
        position: object = (0, 0, 0),
        rotation: object = None,
        scale: object = 1.0,
        origin: object = (0, 0, 0),
        parent: Transform3D | None = None,
    ) -> None:
        self._x = 0.0
        self._y = 0.0
        self._z = 0.0
        self._rotation = Quaternion.identity()
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._scale_z = 1.0
        self._origin_x = 0.0
        self._origin_y = 0.0
        self._origin_z = 0.0
        self._parent: Transform3D | None = None
        self._children: list[Transform3D] = []

        self.position = position
        if rotation is not None:
            self.rotation = rotation
        self.scale = scale
        self.origin = origin
        self.parent = parent

    # -- position ----------------------------------------------------------

    @property
    def position(self) -> Vector3:
        """The local ``(x, y, z)`` position as a :class:`~pydex_ge.physics.Vector3`."""
        return Vector3(self._x, self._y, self._z)

    @position.setter
    def position(self, value: object) -> None:
        vector = _as_vector(value, "position")
        self._x = vector.x
        self._y = vector.y
        self._z = vector.z

    @property
    def x(self) -> float:
        """The x component of the local position."""
        return self._x

    @x.setter
    def x(self, value: object) -> None:
        self._x = _number(value, "x")

    @property
    def y(self) -> float:
        """The y component of the local position."""
        return self._y

    @y.setter
    def y(self, value: object) -> None:
        self._y = _number(value, "y")

    @property
    def z(self) -> float:
        """The z component of the local position."""
        return self._z

    @z.setter
    def z(self, value: object) -> None:
        self._z = _number(value, "z")

    def move(self, dx: object, dy: object, dz: object = 0.0) -> None:
        """Move the transform by ``dx``, ``dy``, ``dz`` world units."""
        self._x += _number(dx, "dx")
        self._y += _number(dy, "dy")
        self._z += _number(dz, "dz")

    # -- rotation ----------------------------------------------------------

    @property
    def rotation(self) -> Quaternion:
        """The local rotation as a :class:`~pydex_ge.math.Quaternion`."""
        return self._rotation.copy()

    @rotation.setter
    def rotation(self, value: object) -> None:
        self._rotation = _as_quaternion(value, "rotation")

    @property
    def rotation_euler(self) -> tuple[float, float, float]:
        """The local rotation as ``(yaw, pitch, roll)`` degrees."""
        return self._rotation.to_euler()

    @rotation_euler.setter
    def rotation_euler(self, value: object) -> None:
        if isinstance(value, (tuple, list)) and len(value) == 3:
            self._rotation = Quaternion.from_euler(value[0], value[1], value[2])
        elif isinstance(value, Quaternion):
            self._rotation = value
        else:
            raise ConfigurationError(
                f"rotation_euler must be a (yaw, pitch, roll) degrees triple, got {value!r}."
            )

    # -- scale -------------------------------------------------------------

    @property
    def scale(self) -> Vector3:
        """The per-axis scale as a :class:`~pydex_ge.physics.Vector3`."""
        return Vector3(self._scale_x, self._scale_y, self._scale_z)

    @scale.setter
    def scale(self, value: object) -> None:
        vector = _as_scale(value)
        self._scale_x = vector.x
        self._scale_y = vector.y
        self._scale_z = vector.z

    @property
    def scale_x(self) -> float:
        """The x scale factor."""
        return self._scale_x

    @scale_x.setter
    def scale_x(self, value: object) -> None:
        self._scale_x = _scale(value, "scale_x")

    @property
    def scale_y(self) -> float:
        """The y scale factor."""
        return self._scale_y

    @scale_y.setter
    def scale_y(self, value: object) -> None:
        self._scale_y = _scale(value, "scale_y")

    @property
    def scale_z(self) -> float:
        """The z scale factor."""
        return self._scale_z

    @scale_z.setter
    def scale_z(self, value: object) -> None:
        self._scale_z = _scale(value, "scale_z")

    # -- origin ------------------------------------------------------------

    @property
    def origin(self) -> Vector3:
        """The local pivot ``(x, y, z)`` as a :class:`~pydex_ge.physics.Vector3`."""
        return Vector3(self._origin_x, self._origin_y, self._origin_z)

    @origin.setter
    def origin(self, value: object) -> None:
        vector = _as_vector(value, "origin")
        self._origin_x = vector.x
        self._origin_y = vector.y
        self._origin_z = vector.z

    # -- parent / children -------------------------------------------------

    @property
    def parent(self) -> Transform3D | None:
        """The parent transform this one inherits world transforms from."""
        return self._parent

    @parent.setter
    def parent(self, value: object) -> None:
        if value is not None and not isinstance(value, Transform3D):
            raise ConfigurationError("parent must be a Transform3D or None.")
        if self._parent is value:
            return
        if value is not None and self._has_descendant(value):
            raise ConfigurationError("parent would create a transform cycle.")
        if self._parent is not None:
            self._parent._children.remove(self)
        self._parent = value
        if value is not None:
            value._children.append(self)

    def _has_descendant(self, candidate: Transform3D) -> bool:
        """True when ``candidate`` is this transform or under it.

        Guards the parent setter so a child cannot become its own ancestor,
        which would make ``world_*`` recurse forever.
        """
        if candidate is self:
            return True
        return any(child._has_descendant(candidate) for child in self._children)

    @property
    def children(self) -> tuple[Transform3D, ...]:
        """A tuple of the direct children of this transform."""
        return tuple(self._children)

    def add_child(self, child: Transform3D) -> Transform3D:
        """Attach ``child`` to this transform (returns it for chaining)."""
        if not isinstance(child, Transform3D):
            raise ConfigurationError("add_child() needs a Transform3D.")
        child.parent = self
        return child

    def remove_child(self, child: Transform3D) -> bool:
        """Detach ``child``.  Returns True when it was a direct child."""
        if not isinstance(child, Transform3D):
            raise ConfigurationError("remove_child() needs a Transform3D.")
        if child._parent is not self:
            return False
        child._parent = None
        self._children.remove(child)
        return True

    # -- local vs world ----------------------------------------------------

    @property
    def local_position(self) -> Vector3:
        """This transform's own ``(x, y, z)`` position (ignores the parent)."""
        return Vector3(self._x, self._y, self._z)

    @property
    def local_rotation(self) -> Quaternion:
        """This transform's own rotation (ignores the parent)."""
        return self._rotation.copy()

    @property
    def local_scale(self) -> Vector3:
        """This transform's own scale (ignores the parent)."""
        return self.scale

    @property
    def world_position(self) -> Vector3:
        """The position in world space.

        A child sits at the parent's world position, offset by the parent's
        rotation applied to its (parent-scale times local) offset.
        """
        if self._parent is None:
            return Vector3(self._x, self._y, self._z)
        parent_scale = self._parent.world_scale
        offset = Vector3(
            self._x * parent_scale.x,
            self._y * parent_scale.y,
            self._z * parent_scale.z,
        )
        rotated = self._parent.world_rotation.rotate_vector(offset)
        parent_pos = self._parent.world_position
        return Vector3(parent_pos.x + rotated.x, parent_pos.y + rotated.y, parent_pos.z + rotated.z)

    @property
    def world_rotation(self) -> Quaternion:
        """The rotation in world space (parent rotation * local rotation)."""
        if self._parent is None:
            return self._rotation.copy()
        return self._parent.world_rotation * self._rotation

    @property
    def world_scale(self) -> Vector3:
        """The scale in world space (parent scale times local scale, per axis)."""
        if self._parent is None:
            return Vector3(self._scale_x, self._scale_y, self._scale_z)
        parent = self._parent.world_scale
        return Vector3(
            parent.x * self._scale_x,
            parent.y * self._scale_y,
            parent.z * self._scale_z,
        )

    def copy(self) -> Transform3D:
        """A new transform with the same values (and no parent/children)."""
        new = Transform3D()
        new.position = Vector3(self._x, self._y, self._z)
        new.rotation = self._rotation.copy()
        new.scale = Vector3(self._scale_x, self._scale_y, self._scale_z)
        new.origin = Vector3(self._origin_x, self._origin_y, self._origin_z)
        return new

    # -- protocol ----------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transform3D):
            return NotImplemented
        return (
            abs(self._x - other._x) < _EPSILON
            and abs(self._y - other._y) < _EPSILON
            and abs(self._z - other._z) < _EPSILON
            and self._rotation == other._rotation
            and abs(self._scale_x - other._scale_x) < _EPSILON
            and abs(self._scale_y - other._scale_y) < _EPSILON
            and abs(self._scale_z - other._scale_z) < _EPSILON
            and abs(self._origin_x - other._origin_x) < _EPSILON
            and abs(self._origin_y - other._origin_y) < _EPSILON
            and abs(self._origin_z - other._origin_z) < _EPSILON
        )

    def __repr__(self) -> str:
        parent = self._parent.__class__.__name__ if self._parent is not None else None
        euler = self.rotation_euler
        return (
            f"Transform3D(position=({self._x!r}, {self._y!r}, {self._z!r}), "
            f"rotation_euler=({euler[0]!r}, {euler[1]!r}, {euler[2]!r}), "
            f"scale={self.scale!r}, origin={self.origin!r}, parent={parent})"
        )


__all__ = ["Transform3D"]
