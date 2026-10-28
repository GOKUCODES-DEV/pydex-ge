"""The :class:`Camera`: a 2D viewport transform for world-space drawing.

A camera describes *which part of the world is visible* and turns world
coordinates into screen coordinates.  World-space objects (sprites,
animations) drawn through an active camera are translated and scaled by
the camera; screen-space UI (labels, text) is not.

The camera is deliberately kept abstract enough to be the base for future
3D support: it holds a viewport, a position, a zoom, follow logic, bounds,
and an enabled flag, and exposes the two coordinate conversions.  A later
Part 9+ ``Camera3D`` can build on the same interface.  PYDEX does not do
3D rendering today.

The convention: ``camera.position`` is the world coordinate shown at the
center of the viewport.
"""

from __future__ import annotations

import math

from ..exceptions import ConfigurationError
from ..physics.rect import Rect
from ..physics.vector import Vector2


def _number(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if positive and number <= 0:
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


class Camera:
    """A 2D camera that converts world coordinates to screen coordinates.

    Parameters
    ----------
    width, height:
        The viewport size in screen pixels (defaults ``800x600``).  Both
        must be positive.
    position:
        The world coordinate shown at the center of the viewport, as a
        :class:`~pydex_ge.physics.Vector2` or an ``(x, y)`` pair.
    zoom:
        How large world objects appear (``1.0`` normal, ``2.0`` twice as
        large, ``0.5`` zoomed out).  Must be positive.

    Example
    -------
    ::

        camera = pydex_ge.Camera(position=(100, 50), zoom=1.0)
        camera.position = (100, 50)
        camera.x += 100
        camera.zoom = 2.0

    In a game: call :meth:`update` every frame with the delta time, then
    draw world objects between :meth:`begin` and :meth:`end` so the renderer
    applies the camera transform.  Labels drawn outside stay screen-space.
    """

    def __init__(
        self,
        width: object = 800,
        height: object = 600,
        *,
        position: object = (0, 0),
        zoom: object = 1.0,
    ) -> None:
        self._width = _number(width, "width", positive=True)
        self._height = _number(height, "height", positive=True)
        self._position = _as_vector(position, "position").copy()
        self._zoom = _number(zoom, "zoom", positive=True)
        self._bounds: Rect | None = None
        self._follow = None
        self._smoothing = 0.0
        self._enabled = True
        self._renderer = None
        self._active = False
        self._dead_zone: tuple[float, float] | None = None
        self._shake_amount = 0.0
        self._shake_duration = 0.0
        self._shake_time = 0.0
        self._shake_x = 0.0
        self._shake_y = 0.0

    # -- viewport ---------------------------------------------------------

    @property
    def width(self) -> float:
        """The viewport width in screen pixels."""
        return self._width

    @property
    def height(self) -> float:
        """The viewport height in screen pixels."""
        return self._height

    @property
    def viewport(self) -> Rect:
        """The viewport rectangle ``Rect(0, 0, width, height)``."""
        return Rect(0, 0, self._width, self._height)

    # -- position ---------------------------------------------------------

    @property
    def position(self) -> Vector2:
        """The world coordinate at the center of the viewport."""
        return self._position

    @position.setter
    def position(self, value: object) -> None:
        self._position = _as_vector(value, "position").copy()

    @property
    def x(self) -> float:
        """The horizontal component of the camera position."""
        return self._position.x

    @x.setter
    def x(self, value: object) -> None:
        self._position.x = _number(value, "x")

    @property
    def y(self) -> float:
        """The vertical component of the camera position."""
        return self._position.y

    @y.setter
    def y(self, value: object) -> None:
        self._position.y = _number(value, "y")

    def move(self, dx: object, dy: object) -> None:
        """Move the camera by ``dx``, ``dy`` world pixels."""
        self._position.x += _number(dx, "dx")
        self._position.y += _number(dy, "dy")

    def look_at(self, position: object) -> None:
        """Center the viewport on ``position``."""
        self._position = _as_vector(position, "position").copy()

    # -- zoom -------------------------------------------------------------

    @property
    def zoom(self) -> float:
        """How large world objects appear (must be positive)."""
        return self._zoom

    @zoom.setter
    def zoom(self, value: object) -> None:
        self._zoom = _number(value, "zoom", positive=True)

    # -- enable / disable -------------------------------------------------

    @property
    def enabled(self) -> bool:
        """True when :meth:`begin` applies the camera transform.

        When disabled, ``begin()`` does nothing, so world objects are drawn
        in raw screen coordinates.
        """
        return self._enabled

    @enabled.setter
    def enabled(self, value: object) -> None:
        if not isinstance(value, bool):
            raise ConfigurationError("enabled must be a bool.")
        self._enabled = value

    # -- bounds -----------------------------------------------------------

    @property
    def bounds(self) -> Rect | None:
        """An optional world :class:`~pydex_ge.physics.Rect` the camera stays inside."""
        return self._bounds

    @bounds.setter
    def bounds(self, value: object) -> None:
        if value is None:
            self._bounds = None
            return
        if not isinstance(value, Rect):
            raise ConfigurationError("camera.bounds must be a Rect or None.")
        self._bounds = value

    # -- following --------------------------------------------------------

    @property
    def smoothing(self) -> float:
        """Follow smoothing factor (``0`` = instant, higher = smoother)."""
        return self._smoothing

    @smoothing.setter
    def smoothing(self, value: object) -> None:
        value = _number(value, "smoothing")
        if value < 0:
            raise ConfigurationError("smoothing must be non-negative.")
        self._smoothing = value

    @property
    def dead_zone(self) -> tuple[float, float] | None:
        """An optional ``(width, height)`` dead zone around the followed object.

        While the followed target stays inside the zone the camera does not
        move; once it exits, the camera follows it again (still eased by
        :attr:`smoothing`).  ``None`` (the default) disables the dead zone.
        """
        return self._dead_zone

    @dead_zone.setter
    def dead_zone(self, value: object) -> None:
        if value is None:
            self._dead_zone = None
            return
        if isinstance(value, (tuple, list)) and len(value) == 2:
            width = _number(value[0], "dead_zone.width")
            height = _number(value[1], "dead_zone.height")
            if width < 0 or height < 0:
                raise ConfigurationError("dead_zone must be non-negative.")
            self._dead_zone = (width, height)
            return
        raise ConfigurationError(
            "camera.dead_zone must be a (width, height) pair or None."
        )

    def follow(self, target: object, smoothing: object | None = None) -> None:
        """Follow a target's position.

        The target can be a :class:`~pydex_ge.physics.Vector2`, an ``(x, y)``
        pair, or any object exposing a ``position`` (e.g. a
        :class:`~pydex_ge.physics.Body`) or ``x``/``y`` attributes (e.g. a
        :class:`~pydex_ge.graphics.Sprite`).  Use :attr:`smoothing` (or the
        optional ``smoothing`` argument) for a gradual approach;
        ``0`` follows instantly.
        """
        self._resolve_target_position(target)  # validate now
        self._follow = target
        if smoothing is not None:
            self.smoothing = smoothing

    def clear_target(self) -> None:
        """Stop following; the camera stays where it is."""
        self._follow = None

    def clear_follow(self) -> None:
        """Alias for :meth:`clear_target`."""
        self._follow = None

    def _resolve_target_position(self, target: object) -> Vector2:
        if isinstance(target, Vector2):
            return target
        if isinstance(target, (tuple, list)) and len(target) == 2:
            return Vector2(target[0], target[1])
        if hasattr(target, "world_position"):
            return _as_vector(target.world_position, "target.world_position")
        if hasattr(target, "position"):
            return _as_vector(target.position, "target.position")
        if hasattr(target, "x") and hasattr(target, "y"):
            return Vector2(target.x, target.y)
        raise ConfigurationError(
            "camera.follow() needs a Vector2, an (x, y) pair, or an object "
            f"with a position (or x/y), got {target!r}."
        )

    # -- camera shake -----------------------------------------------------

    def shake(self, amount: object = 5, duration: object = 0.25) -> None:
        """Shake the view by ``amount`` pixels for ``duration`` seconds.

        The shake is deterministic (no random numbers), decays linearly to
        zero, expires automatically, and ends exactly at ``(0, 0)``.  Calling
        :meth:`shake` again replaces the previous shake.  Shake is *visual
        only*: it never moves sprites, bodies, or the world — it is applied
        inside :meth:`world_to_screen` / :meth:`screen_to_world`.
        """
        amount = _number(amount, "amount")
        duration = _number(duration, "duration")
        if amount < 0:
            raise ConfigurationError("amount must be non-negative.")
        if duration < 0:
            raise ConfigurationError("duration must be non-negative.")
        if duration == 0:
            self._shake_amount = 0.0
            self._shake_duration = 0.0
            self._shake_time = 0.0
            self._shake_x = 0.0
            self._shake_y = 0.0
            return
        self._shake_amount = amount
        self._shake_duration = duration
        self._shake_time = 0.0

    @property
    def shake_offset(self) -> tuple[float, float]:
        """The current visual shake offset as ``(dx, dy)`` (``(0, 0)`` when idle)."""
        return (self._shake_x, self._shake_y)

    @property
    def shaking(self) -> bool:
        """True while a shake is still active."""
        return self._shake_duration > 0

    def _advance_shake(self, dt: float) -> None:
        if self._shake_duration <= 0:
            return
        self._shake_time += dt
        if self._shake_time >= self._shake_duration:
            self._shake_duration = 0.0
            self._shake_amount = 0.0
            self._shake_time = 0.0
            self._shake_x = 0.0
            self._shake_y = 0.0
            return
        progress = self._shake_time / self._shake_duration
        amplitude = self._shake_amount * (1.0 - progress)
        phase = self._shake_time * 37.0
        self._shake_x = math.sin(phase * 1.3) * amplitude
        self._shake_y = math.cos(phase * 1.7) * amplitude

    # -- coordinate conversion --------------------------------------------

    def world_to_screen(self, position: object) -> Vector2:
        """Convert a world position to a screen position (zoom and shake aware)."""
        world = _as_vector(position, "position")
        return Vector2(
            (world.x - self._position.x) * self._zoom + self._width / 2 + self._shake_x,
            (world.y - self._position.y) * self._zoom + self._height / 2 + self._shake_y,
        )

    def screen_to_world(self, position: object) -> Vector2:
        """Convert a screen position to a world position (zoom and shake aware).

        The inverse of :meth:`world_to_screen` within floating-point
        tolerance.
        """
        screen = _as_vector(position, "position")
        return Vector2(
            (screen.x - self._width / 2 - self._shake_x) / self._zoom + self._position.x,
            (screen.y - self._height / 2 - self._shake_y) / self._zoom + self._position.y,
        )

    # -- per-frame step ---------------------------------------------------

    def update(self, dt: object) -> None:
        """Advance follow smoothing and shake; keep the camera inside :attr:`bounds`.

        Call once per frame with the game's delta time, e.g. in
        ``Game.update``.
        """
        if isinstance(dt, bool) or not isinstance(dt, (int, float)):
            raise ConfigurationError(f"dt must be a number, got {dt!r}.")
        dt = float(dt)
        if dt < 0:
            raise ConfigurationError("dt must be non-negative.")

        if self._follow is not None:
            target = self._resolve_target_position(self._follow)
            if self._dead_zone is not None:
                half_w = self._dead_zone[0] / 2.0
                half_h = self._dead_zone[1] / 2.0
                dx = target.x - self._position.x
                dy = target.y - self._position.y
                want_x = 0.0 if abs(dx) <= half_w else (abs(dx) - half_w) * (1.0 if dx > 0 else -1.0)
                want_y = 0.0 if abs(dy) <= half_h else (abs(dy) - half_h) * (1.0 if dy > 0 else -1.0)
                goal = Vector2(self._position.x + want_x, self._position.y + want_y)
                if self._smoothing > 0:
                    factor = 1.0 - math.exp(-self._smoothing * dt)
                    new_x = self._position.x + (goal.x - self._position.x) * factor
                    new_y = self._position.y + (goal.y - self._position.y) * factor
                    self._position = Vector2(new_x, new_y)
                else:
                    self._position = goal
            elif self._smoothing > 0:
                factor = 1.0 - math.exp(-self._smoothing * dt)
                new_x = self._position.x + (target.x - self._position.x) * factor
                new_y = self._position.y + (target.y - self._position.y) * factor
                self._position = Vector2(new_x, new_y)
            else:
                self._position = target.copy()
        self._advance_shake(dt)
        self._clamp_to_bounds()

    def _clamp_to_bounds(self) -> None:
        if self._bounds is None:
            return
        bounds = self._bounds
        visible_w = self._width / self._zoom
        visible_h = self._height / self._zoom
        half_w = visible_w / 2
        half_h = visible_h / 2

        if bounds.width <= visible_w:
            x = bounds.center.x
        else:
            x = min(max(self._position.x, bounds.left + half_w), bounds.right - half_w)
        if bounds.height <= visible_h:
            y = bounds.center.y
        else:
            y = min(max(self._position.y, bounds.top + half_h), bounds.bottom - half_h)
        self._position = Vector2(x, y)

    # -- renderer integration --------------------------------------------

    def attach(self, renderer) -> None:
        """Remember ``renderer`` so :meth:`begin` can be called without an argument."""
        if renderer is None:
            raise ConfigurationError("Camera.attach() needs a renderer.")
        self._renderer = renderer

    def begin(self, renderer=None) -> None:
        """Make the renderer draw subsequent world objects through this camera.

        ``renderer`` may be omitted if :meth:`attach` was called first.
        Labels and text drawn between :meth:`begin` and :meth:`end` are
        **not** transformed; draw them after :meth:`end` for fixed screen
        UI.  No-op when :attr:`enabled` is ``False``.
        """
        if not self._enabled:
            return
        if self._active:
            return
        target = renderer if renderer is not None else self._renderer
        if target is None:
            raise ConfigurationError(
                "Camera needs a renderer: pass one to begin(renderer) or call attach(renderer)."
            )
        self._renderer = target
        target.begin_camera(self)
        self._active = True

    def end(self) -> None:
        """Undo :meth:`begin`; world objects are drawn untransformed again."""
        if not self._active:
            if self._enabled:
                raise ConfigurationError("Camera.end() called without a matching begin().")
            return
        if getattr(self._renderer, "active_camera", None) is not self:
            raise ConfigurationError(
                "Camera.end() cannot end: a different camera is active on the renderer."
            )
        self._renderer.end_camera()
        self._active = False


class Camera2D(Camera):
    """Alias of :class:`Camera` kept for clarity alongside future 3D cameras.

    Part 8 only implements the 2D camera.  ``pydex_ge.Camera2D(...)`` behaves
    exactly like ``pydex_ge.Camera(...)`` so the API can grow a ``Camera3D``
    later without breaking existing code.
    """


__all__ = ["Camera", "Camera2D"]
