"""The :class:`Body`: a simple physics object.

A :class:`Body` is the PYDEX building block for simple movement.  It holds
a top-left ``position``, a ``velocity``, an ``acceleration``, a ``mass``,
and a ``size``, and integrates them in :meth:`update`.

This is deliberately *not* a rigid body: there is no rotation, friction,
restitution, or torque.  Bodies move, accelerate, and collide with static
rectangles; that is the whole Part 7.5 scope.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .rect import Rect
from .vector import Vector2


def _number(value: object, name: str, *, non_negative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if non_negative and number < 0:
        raise ConfigurationError(f"{name} must be non-negative, got {value!r}.")
    return number


def _positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if number <= 0:
        raise ConfigurationError(f"{name} must be greater than zero, got {value!r}.")
    return number


def _as_vector(value: object, name: str) -> Vector2:
    if isinstance(value, Vector2):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Vector2(value[0], value[1])
    raise ConfigurationError(
        f"{name} must be a Vector2 or a 2-element (x, y) sequence, got {value!r}."
    )


def _as_rect(value: object, name: str) -> Rect:
    if isinstance(value, Rect):
        return value
    raise ConfigurationError(f"{name} must be a Rect, got {value!r}.")


class Body:
    """A simple moving object.

    Parameters
    ----------
    position:
        The top-left corner as a :class:`~pydex_ge.physics.Vector2` or a
        ``(x, y)`` sequence (default ``(0, 0)``).
    size:
        The ``(width, height)`` as a sequence or :class:`~pydex_ge.physics.Vector2`
        (default ``(1, 1)``).
    velocity:
        Initial velocity (default ``(0, 0)``).
    acceleration:
        Constant acceleration (default ``(0, 0)``).
    mass:
        The body mass (default ``1.0``).  Must be greater than zero.
    """

    __slots__ = (
        "_position",
        "_velocity",
        "_acceleration",
        "_mass",
        "_width",
        "_height",
    )

    def __init__(
        self,
        *,
        position=(0, 0),
        size=(1, 1),
        velocity=(0, 0),
        acceleration=(0, 0),
        mass: object = 1.0,
    ) -> None:
        self._position = _as_vector(position, "position").copy()
        self._velocity = _as_vector(velocity, "velocity").copy()
        self._acceleration = _as_vector(acceleration, "acceleration").copy()
        self._mass = _positive(mass, "mass")
        size = _as_vector(size, "size")
        self._width = _number(size.x, "width", non_negative=True)
        self._height = _number(size.y, "height", non_negative=True)

    # -- components -------------------------------------------------------

    @property
    def position(self) -> Vector2:
        """The top-left corner of the body (a :class:`~pydex_ge.physics.Vector2`)."""
        return self._position

    @position.setter
    def position(self, value: object) -> None:
        self._position = _as_vector(value, "position").copy()

    @property
    def velocity(self) -> Vector2:
        """The velocity in pixels per second (a :class:`~pydex_ge.physics.Vector2`)."""
        return self._velocity

    @velocity.setter
    def velocity(self, value: object) -> None:
        self._velocity = _as_vector(value, "velocity").copy()

    @property
    def acceleration(self) -> Vector2:
        """The constant acceleration in pixels per second squared."""
        return self._acceleration

    @acceleration.setter
    def acceleration(self, value: object) -> None:
        self._acceleration = _as_vector(value, "acceleration").copy()

    @property
    def mass(self) -> float:
        """The body mass (used by :meth:`apply_force`)."""
        return self._mass

    @mass.setter
    def mass(self, value: object) -> None:
        self._mass = _positive(value, "mass")

    @property
    def width(self) -> float:
        """The body width in pixels."""
        return self._width

    @width.setter
    def width(self, value: object) -> None:
        self._width = _number(value, "width", non_negative=True)

    @property
    def height(self) -> float:
        """The body height in pixels."""
        return self._height

    @height.setter
    def height(self, value: object) -> None:
        self._height = _number(value, "height", non_negative=True)

    @property
    def size(self) -> Vector2:
        """The ``(width, height)`` as a :class:`~pydex_ge.physics.Vector2`."""
        return Vector2(self._width, self._height)

    @property
    def rect(self) -> Rect:
        """The body's collision rectangle at its current position."""
        return Rect(self._position.x, self._position.y, self._width, self._height)

    # -- integration ------------------------------------------------------

    def update(self, dt: object) -> None:
        """Integrate one time step of ``dt`` seconds.

        Uses semi-implicit Euler: velocity is updated from acceleration
        first, then position from the new velocity.  This keeps the motion
        stable for simple games.
        """
        dt = _number(dt, "dt")
        if dt < 0:
            raise ConfigurationError("dt must be non-negative.")
        self._velocity += self._acceleration * dt
        self._position += self._velocity * dt

    # -- forces -----------------------------------------------------------

    def apply_force(self, force: object) -> None:
        """Apply a force (in pixels/second squared) scaled by ``1 / mass``.

        The force is added to :attr:`acceleration` each time it is called.
        """
        force = _as_vector(force, "force")
        self._acceleration += force / self._mass

    def apply_impulse(self, impulse: object) -> None:
        """Apply an instantaneous impulse, changing the velocity directly.

        Useful for jumps and one-shot kicks.
        """
        impulse = _as_vector(impulse, "impulse")
        self._velocity += impulse

    # -- collision --------------------------------------------------------

    def collides_with(self, other: object) -> bool:
        """True when this body's rectangle overlaps ``other`` (a ``Rect``)."""
        other = _as_rect(other, "other")
        return self.rect.overlaps(other)

    def collide_static(self, other: object) -> bool:
        """Resolve a collision against a static rectangle ``other``.

        If the body overlaps the rectangle, it is pushed out on the side it
        is moving toward (velocity-aware resolution) and the matching
        velocity component is zeroed, so a falling body lands on top of a
        floor instead of being ejected through a side.  When the body has
        no velocity (or is already embedded), the axis of least penetration
        is used.  Touching without any penetration is not treated as a
        collision.  Returns True when a collision was resolved.
        """
        other = _as_rect(other, "other")
        rect = self.rect
        if not rect.overlaps(other):
            return False

        overlap_left = rect.right - other.left      # exit through the left side
        overlap_right = other.right - rect.left     # exit through the right side
        overlap_top = rect.bottom - other.top       # exit above (land on top)
        overlap_bottom = other.bottom - rect.top    # exit below (hit a ceiling)

        min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
        if min_overlap <= 0:
            return False

        # Prefer the face the body is moving into; embedded/stationary
        # bodies fall back to the shallowest exit.
        candidates: list[tuple[str, float]] = []
        if self._velocity.x > 0:
            candidates.append(("left", overlap_left))
        if self._velocity.x < 0:
            candidates.append(("right", overlap_right))
        if self._velocity.y > 0:
            candidates.append(("top", overlap_top))
        if self._velocity.y < 0:
            candidates.append(("bottom", overlap_bottom))
        if not candidates:
            candidates = [
                ("left", overlap_left),
                ("right", overlap_right),
                ("top", overlap_top),
                ("bottom", overlap_bottom),
            ]
        face = min(candidates, key=lambda item: item[1])[0]

        if face == "left":
            self._position.x = other.left - self._width
            self._velocity.x = 0.0
        elif face == "right":
            self._position.x = other.right
            self._velocity.x = 0.0
        elif face == "top":
            self._position.y = other.top - self._height
            self._velocity.y = 0.0
        else:
            self._position.y = other.bottom
            self._velocity.y = 0.0
        return True

    # -- protocol ---------------------------------------------------------

    def copy(self) -> Body:
        """A new body with the same position, size, velocity, and mass."""
        return Body(
            position=self._position,
            size=(self._width, self._height),
            velocity=self._velocity,
            acceleration=self._acceleration,
            mass=self._mass,
        )

    def __repr__(self) -> str:
        return (
            f"Body(position={self._position!r}, size=({self._width!r}, "
            f"{self._height!r}), velocity={self._velocity!r})"
        )


__all__ = ["Body"]
