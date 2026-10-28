"""The :class:`Transform2D`: a reusable 2D transformation object.

A transform holds a position, a rotation (in degrees), a scale (uniform
``2`` or per-axis ``(2, 1)``), a normalized origin ``(0, 0)`` top-left to
``(0.5, 0.5)`` center, and an optional parent.  Child transforms inherit
their parent's movement:

* world position follows the parent,
* world rotation = parent rotation + local rotation,
* world scale = component-wise multiplication of the two scales.

This is the same math the Part 12 ``Sprite`` transform support uses, so a
:class:`Transform2D` and a :class:`~pydex_ge.graphics.sprite.Sprite` can be
used interchangeably as a sprite ``parent``.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from ..physics.vector import Vector2
from .transform3d import Transform3D

_EPSILON = 1e-9


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    return float(value)


def _as_vector(value: object, name: str) -> Vector2:
    if isinstance(value, Vector2):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Vector2(value[0], value[1])
    raise ConfigurationError(
        f"{name} must be a Vector2 or a 2-element (x, y) sequence, got {value!r}."
    )


def _as_scale(value: object) -> tuple[float, float]:
    """Normalize a scale value (a number or an ``(x, y)`` pair) to two floats."""
    if isinstance(value, (tuple, list)):
        if len(value) != 2:
            raise ConfigurationError(
                f"scale must be a number or a 2-element (x, y) pair, got {value!r}."
            )
        sx, sy = value[0], value[1]
    elif isinstance(value, Vector2):
        sx, sy = value.x, value.y
    else:
        sx = sy = value
    return _scale(sx, "scale"), _scale(sy, "scale")


def _scale(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number greater than zero, got {value!r}.")
    number = float(value)
    if number <= 0:
        raise ConfigurationError(f"{name} must be a number greater than zero, got {value!r}.")
    return number


class Transform2D:
    """A position, rotation, scale, and origin with optional parent/child links.

    Parameters
    ----------
    position:
        The local ``(x, y)`` position (a :class:`~pydex_ge.physics.Vector2` or
        an ``(x, y)`` pair).  Defaults to ``(0, 0)``.
    rotation:
        Clockwise rotation in degrees.  Defaults to ``0``.
    scale:
        A uniform scale ``2`` or a per-axis ``(2, 1)`` pair.  Must be
        greater than zero.  Defaults to ``1``.
    origin:
        A normalized ``(origin_x, origin_y)`` pair where ``(0, 0)`` is the
        top-left and ``(0.5, 0.5)`` is the center.  Defaults to ``(0, 0)``.
    parent:
        An optional parent :class:`Transform2D`.

    Example
    -------
    ::

        ship = pydex_ge.Transform2D(position=(100, 50), rotation=45, scale=(2, 1))
        gun = pydex_ge.Transform2D(position=(20, 0), parent=ship)
        ship.position = (200, 80)      # gun follows automatically
        gun.world_position             # (220, 80)

    Values are validated; ``bool`` is rejected (it is not a number).
    """

    def __init__(
        self,
        *,
        position: object = (0, 0),
        rotation: object = 0.0,
        scale: object = 1.0,
        origin: object = (0, 0),
        parent: Transform2D | None = None,
    ) -> None:
        self._x = 0.0
        self._y = 0.0
        self._rotation = 0.0
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._origin_x = 0.0
        self._origin_y = 0.0
        self._parent: Transform2D | None = None
        self._children: list[Transform2D] = []

        self.position = position
        self.rotation = rotation
        self.scale = scale
        self.origin = origin
        self.parent = parent

    # -- position ----------------------------------------------------------

    @property
    def position(self) -> Vector2:
        """The local ``(x, y)`` position as a :class:`~pydex_ge.physics.Vector2`."""
        return Vector2(self._x, self._y)

    @position.setter
    def position(self, value: object) -> None:
        vector = _as_vector(value, "position")
        self._x = vector.x
        self._y = vector.y

    @property
    def x(self) -> float:
        """The horizontal component of the local position."""
        return self._x

    @x.setter
    def x(self, value: object) -> None:
        self._x = _number(value, "x")

    @property
    def y(self) -> float:
        """The vertical component of the local position."""
        return self._y

    @y.setter
    def y(self, value: object) -> None:
        self._y = _number(value, "y")

    def move(self, dx: object, dy: object) -> None:
        """Move the transform by ``dx``, ``dy`` world pixels."""
        self._x += _number(dx, "dx")
        self._y += _number(dy, "dy")

    # -- rotation ----------------------------------------------------------

    @property
    def rotation(self) -> float:
        """Clockwise rotation in degrees."""
        return self._rotation

    @rotation.setter
    def rotation(self, value: object) -> None:
        self._rotation = _number(value, "rotation")

    # -- scale -------------------------------------------------------------

    @property
    def scale(self) -> float | tuple[float, float]:
        """The scale: a float when uniform, else an ``(x, y)`` pair."""
        return self._format_scale(self._scale_x, self._scale_y)

    @scale.setter
    def scale(self, value: object) -> None:
        self._scale_x, self._scale_y = _as_scale(value)

    @property
    def scale_x(self) -> float:
        """The horizontal scale factor."""
        return self._scale_x

    @scale_x.setter
    def scale_x(self, value: object) -> None:
        self._scale_x = _scale(value, "scale_x")

    @property
    def scale_y(self) -> float:
        """The vertical scale factor."""
        return self._scale_y

    @scale_y.setter
    def scale_y(self, value: object) -> None:
        self._scale_y = _scale(value, "scale_y")

    # -- origin ------------------------------------------------------------

    @property
    def origin(self) -> tuple[float, float]:
        """The normalized origin ``(origin_x, origin_y)`` (``(0.5, 0.5)`` = center)."""
        return (self._origin_x, self._origin_y)

    @origin.setter
    def origin(self, value: object) -> None:
        vector = _as_vector(value, "origin")
        self._origin_x = vector.x
        self._origin_y = vector.y

    # -- parent / children -------------------------------------------------

    @property
    def parent(self) -> Transform2D | None:
        """The parent transform this one inherits world transforms from."""
        return self._parent

    @parent.setter
    def parent(self, value: object) -> None:
        if value is not None and not isinstance(value, Transform2D):
            raise ConfigurationError("parent must be a Transform2D or None.")
        if self._parent is value:
            return
        if value is not None and self._has_descendant(value):
            raise ConfigurationError("parent would create a transform cycle.")
        if self._parent is not None:
            self._parent._children.remove(self)
        self._parent = value
        if value is not None:
            value._children.append(self)

    def _has_descendant(self, candidate: Transform2D) -> bool:
        """True when ``candidate`` is this transform or under it.

        Guards the parent setter so a child cannot become its own ancestor,
        which would make ``world_*`` recurse forever.
        """
        if candidate is self:
            return True
        return any(child._has_descendant(candidate) for child in self._children)

    @property
    def children(self) -> tuple[Transform2D, ...]:
        """A tuple of the direct children of this transform."""
        return tuple(self._children)

    def add_child(self, child: Transform2D) -> Transform2D:
        """Attach ``child`` to this transform (returns it for chaining)."""
        if not isinstance(child, Transform2D):
            raise ConfigurationError("add_child() needs a Transform2D.")
        child.parent = self
        return child

    def remove_child(self, child: Transform2D) -> bool:
        """Detach ``child``.  Returns True when it was a direct child."""
        if not isinstance(child, Transform2D):
            raise ConfigurationError("remove_child() needs a Transform2D.")
        if child._parent is not self:
            return False
        child._parent = None
        self._children.remove(child)
        return True

    # -- local vs world ----------------------------------------------------

    @property
    def local_position(self) -> Vector2:
        """This transform's own ``(x, y)`` position (ignores the parent)."""
        return Vector2(self._x, self._y)

    @property
    def local_rotation(self) -> float:
        """This transform's own rotation in degrees (ignores the parent)."""
        return self._rotation

    @property
    def local_scale(self) -> float | tuple[float, float]:
        """This transform's own scale (ignores the parent)."""
        return self.scale

    @property
    def world_position(self) -> Vector2:
        """The position in world space.

        A child's local offset is scaled and rotated with its parent, so a
        ``(10, 0)`` offset under a rotated and scaled parent orbits around
        the parent exactly like the rendered sprite does.
        """
        if self._parent is None:
            return Vector2(self._x, self._y)
        offset = Vector2(self._x, self._y)
        parent_scale = self._parent.world_scale
        if isinstance(parent_scale, (tuple, list)):
            offset = Vector2(offset.x * parent_scale[0], offset.y * parent_scale[1])
        else:
            offset = Vector2(offset.x * parent_scale, offset.y * parent_scale)
        offset = offset.rotate(self._parent.world_rotation)
        parent = self._parent.world_position
        return Vector2(parent.x + offset.x, parent.y + offset.y)

    @property
    def world_rotation(self) -> float:
        """The rotation in world space (parent rotation + local rotation)."""
        if self._parent is None:
            return self._rotation
        return self._parent.world_rotation + self._rotation

    @property
    def world_scale(self) -> float | tuple[float, float]:
        """The scale in world space (parent scale times local scale, per axis)."""
        if self._parent is None:
            return self.scale
        parent = self._parent.world_scale
        if isinstance(parent, (tuple, list)):
            px, py = parent[0], parent[1]
        else:
            px = py = parent
        return self._format_scale(px * self._scale_x, py * self._scale_y)

    @staticmethod
    def _format_scale(sx: float, sy: float) -> float | tuple[float, float]:
        if abs(sx - sy) < _EPSILON:
            return sx
        return (sx, sy)

    # -- protocol ----------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transform2D):
            return NotImplemented
        return (
            abs(self._x - other._x) < _EPSILON
            and abs(self._y - other._y) < _EPSILON
            and abs(self._rotation - other._rotation) < _EPSILON
            and abs(self._scale_x - other._scale_x) < _EPSILON
            and abs(self._scale_y - other._scale_y) < _EPSILON
            and abs(self._origin_x - other._origin_x) < _EPSILON
            and abs(self._origin_y - other._origin_y) < _EPSILON
        )

    def __repr__(self) -> str:
        parent = self._parent.__class__.__name__ if self._parent is not None else None
        return (
            f"Transform2D(position=({self._x!r}, {self._y!r}), "
            f"rotation={self._rotation!r}, scale={self.scale!r}, "
            f"origin={self.origin!r}, parent={parent})"
        )


__all__ = ["Transform2D", "Transform3D"]
