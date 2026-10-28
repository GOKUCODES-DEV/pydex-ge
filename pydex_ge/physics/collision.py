"""Geometry-only collision predicates for PYDEX.

These helpers answer *"do these two shapes touch?"* — nothing more.  They
are pure math with no simulation, resolution, or side effects.  All
functions validate their inputs and raise a clear
:class:`~pydex_ge.exceptions.ConfigurationError` on invalid values (bools,
non-numbers, or negative radii).
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .rect import Rect
from .vector import Vector2


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


def _radius(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    radius = float(value)
    if radius < 0:
        raise ConfigurationError(f"{name} must be non-negative, got {value!r}.")
    return radius


def point_in_rect(point: object, rect: object) -> bool:
    """True when ``point`` is on or inside ``rect``."""
    point = _as_vector(point, "point")
    rect = _as_rect(rect, "rect")
    return rect.contains_point(point)


def rects_overlap(a: object, b: object) -> bool:
    """True when rect ``a`` overlaps rect ``b`` (touching edges count)."""
    a = _as_rect(a, "a")
    b = _as_rect(b, "b")
    return a.overlaps(b)


def circles_overlap(
    center_a: object,
    radius_a: object,
    center_b: object,
    radius_b: object,
) -> bool:
    """True when two circles overlap (touching counts).

    Parameters
    ----------
    center_a, center_b:
        The circle centers as :class:`~pydex_ge.physics.Vector2` or ``(x, y)``.
    radius_a, radius_b:
        The circle radii (non-negative).
    """
    center_a = _as_vector(center_a, "center_a")
    center_b = _as_vector(center_b, "center_b")
    radius_a = _radius(radius_a, "radius_a")
    radius_b = _radius(radius_b, "radius_b")
    dx = center_a.x - center_b.x
    dy = center_a.y - center_b.y
    distance_squared = dx * dx + dy * dy
    return distance_squared <= (radius_a + radius_b) ** 2


def point_in_circle(point: object, center: object, radius: object) -> bool:
    """True when ``point`` is on or inside the circle."""
    point = _as_vector(point, "point")
    center = _as_vector(center, "center")
    radius = _radius(radius, "radius")
    dx = point.x - center.x
    dy = point.y - center.y
    return dx * dx + dy * dy <= radius * radius


def circle_rect_overlap(center: object, radius: object, rect: object) -> bool:
    """True when a circle overlaps a rectangle (touching counts).

    Uses the closest-point-on-rectangle test: the circle overlaps when its
    center is within ``radius`` of the nearest point inside the rectangle.
    """
    center = _as_vector(center, "center")
    radius = _radius(radius, "radius")
    rect = _as_rect(rect, "rect")
    closest_x = min(max(center.x, rect.left), rect.right)
    closest_y = min(max(center.y, rect.top), rect.bottom)
    dx = center.x - closest_x
    dy = center.y - closest_y
    return dx * dx + dy * dy <= radius * radius


__all__ = [
    "circle_rect_overlap",
    "circles_overlap",
    "point_in_circle",
    "point_in_rect",
    "rects_overlap",
]
