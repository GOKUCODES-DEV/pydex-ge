"""The :class:`World`: a tiny container that steps physics bodies.

A :class:`World` holds a list of :class:`~pydex_ge.physics.Body` objects,
applies gravity to each, and steps them forward every frame with one call:
:meth:`update`.  It can also resolve bodies against a list of static
rectangles (floors, walls, platforms).

This is intentionally minimal — no broad-phase, no body-to-body
collisions, no rigid-body features.
"""

from __future__ import annotations

import math

from ..exceptions import ConfigurationError
from .body import Body
from .rect import Rect
from .vector import Vector2

#: Hard ceiling on how many sub-steps a single :meth:`World.update`
#: may be split into.  Fast bodies still resolve correctly up to this
#: limit; anything that needs more is a sign of a pathological set-up.
_MAX_SUB_STEPS = 256


def _as_vector(value: object, name: str) -> Vector2:
    if isinstance(value, Vector2):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Vector2(value[0], value[1])
    raise ConfigurationError(
        f"{name} must be a Vector2 or a 2-element (x, y) sequence, got {value!r}."
    )


class World:
    """A simple physics world that steps :class:`~pydex_ge.physics.Body` objects.

    Parameters
    ----------
    gravity:
        Gravity applied to every body, in pixels/second squared, as a
        :class:`~pydex_ge.physics.Vector2` or ``(x, y)`` sequence (default
        ``(0, 500)`` — straight down).
    static_rects:
        Optional iterable of static :class:`~pydex_ge.physics.Rect` objects
        (floors, walls, platforms) that bodies are resolved against each
        step.
    """

    def __init__(
        self,
        *,
        gravity=(0, 500),
        static_rects=(),
    ) -> None:
        self._gravity = _as_vector(gravity, "gravity").copy()
        self._bodies: list[Body] = []
        self._static_rects: list[Rect] = []
        for rect in static_rects:
            if not isinstance(rect, Rect):
                raise ConfigurationError(
                    f"static_rects entries must be Rect objects, got {rect!r}."
                )
            self._static_rects.append(rect)

    # -- gravity ----------------------------------------------------------

    @property
    def gravity(self) -> Vector2:
        """Gravity in pixels/second squared (a :class:`~pydex_ge.physics.Vector2`)."""
        return self._gravity

    @gravity.setter
    def gravity(self, value: object) -> None:
        self._gravity = _as_vector(value, "gravity").copy()

    # -- bodies -----------------------------------------------------------

    @property
    def bodies(self) -> list[Body]:
        """The list of bodies currently in the world."""
        return self._bodies

    @property
    def static_rects(self) -> list[Rect]:
        """The static rectangles bodies collide with."""
        return self._static_rects

    def add_body(self, body: object) -> Body:
        """Add a body to the world and return it."""
        if not isinstance(body, Body):
            raise ConfigurationError(f"add_body expects a Body, got {body!r}.")
        if body not in self._bodies:
            self._bodies.append(body)
        return body

    def remove_body(self, body: object) -> None:
        """Remove a body from the world (no-op if it is not present)."""
        if isinstance(body, Body) and body in self._bodies:
            self._bodies.remove(body)

    def clear(self) -> None:
        """Remove every body from the world."""
        self._bodies.clear()

    def __len__(self) -> int:
        return len(self._bodies)

    def __iter__(self):
        return iter(self._bodies)

    # -- stepping ---------------------------------------------------------

    def update(self, dt: object) -> None:
        """Advance the world by ``dt`` seconds.

        Each body gets gravity applied to its velocity, is stepped, and is
        then resolved against every static rectangle.

        To stop fast bodies from tunnelling through thin walls, floors and
        ceilings, the step is sub-divided so no single integration step can
        carry a body completely past a static rectangle.  The results for
        ordinary (slow) motion are identical to a single step.
        """
        if isinstance(dt, bool) or not isinstance(dt, (int, float)):
            raise ConfigurationError("dt must be a number.")
        if float(dt) < 0:
            raise ConfigurationError("dt must be non-negative.")
        dt = float(dt)
        sub_dt, steps = self._sub_step(dt)
        for _ in range(steps):
            for body in self._bodies:
                body.velocity += self._gravity * sub_dt
                body.update(sub_dt)
                for rect in self._static_rects:
                    body.collide_static(rect)

    def _sub_step(self, dt: float) -> tuple[float, int]:
        """Return ``(sub_dt, step_count)`` guarding against tunnelling.

        Chooses a step size no larger than the thinnest static rectangle
        so a moving body can never jump from one side of a solid to the
        other without ever overlapping it.  With no static rectangles (or
        no bodies) a single full step is taken.
        """
        if dt <= 0 or not self._bodies or not self._static_rects:
            return dt, 1
        thinnest = float("inf")
        for rect in self._static_rects:
            thinnest = min(thinnest, rect.width, rect.height)
        if not math.isfinite(thinnest) or thinnest <= 0:
            thinnest = 1.0
        gravity = self._gravity.length
        max_speed = 0.0
        for body in self._bodies:
            speed = body.velocity.length + gravity * dt
            if speed > max_speed:
                max_speed = speed
        max_move = max_speed * dt
        steps = 1
        if max_move > thinnest:
            steps = min(int(math.ceil(max_move / thinnest)), _MAX_SUB_STEPS)
        return dt / steps, steps

    def __repr__(self) -> str:
        return f"World(gravity={self._gravity!r}, bodies={len(self._bodies)})"


__all__ = ["World"]
