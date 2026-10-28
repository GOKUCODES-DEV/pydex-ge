"""Physics subsystem for PYDEX.

Part 7 provides a **math/geometry foundation**: 2D vectors, rectangles,
and geometry-only collision predicates.  Part 7.5 adds a small **physics
foundation** on top: simple objects (:class:`~pydex_ge.physics.body.Body`)
with position/velocity/acceleration/mass, a tiny
:class:`~pydex_ge.physics.world.World` that applies gravity and steps bodies,
and basic resolution against static rectangles (floors, walls).

This is deliberately *not* a rigid-body physics engine — there is no
rotation, friction, restitution, body-to-body collision, or simulation
beyond these primitives.

Public API:

* :class:`~pydex_ge.physics.vector.Vector2` — a 2D float vector with the
  usual arithmetic and geometry helpers.
* :class:`~pydex_ge.physics.rect.Rect` — an axis-aligned rectangle.
* :class:`~pydex_ge.physics.body.Body` — a simple moving object.
* :class:`~pydex_ge.physics.world.World` — steps bodies with gravity and
  static-rectangle collisions.
* Collision predicates — ``point_in_rect``, ``rects_overlap``,
  ``circles_overlap``, ``point_in_circle``, and ``circle_rect_overlap``.
"""

from .body import Body
from .collision import (
    circle_rect_overlap,
    circles_overlap,
    point_in_circle,
    point_in_rect,
    rects_overlap,
)
from .rect import Rect
from .vector import Vector2
from .vector3 import Vector3
from .world import World

__all__ = [
    "Body",
    "Rect",
    "Vector2",
    "Vector3",
    "World",
    "circle_rect_overlap",
    "circles_overlap",
    "point_in_circle",
    "point_in_rect",
    "rects_overlap",
]
