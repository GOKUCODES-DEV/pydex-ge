"""The :class:`DirectionalLight`: a simple sun-style light for 3D scenes.

A directional light shines from an infinitely far direction, so every
surface with the same orientation receives the same light.  The 3D
renderer computes the diffuse term as ``max(0, dot(normal, -direction))``
scaled by ``intensity`` and the light color.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from ..physics.vector3 import Vector3
from .color import normalize_rgb


def _intensity(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"intensity must be a number between 0 and 1, got {value!r}.")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ConfigurationError(f"intensity must be a number between 0 and 1, got {value!r}.")
    return number


class DirectionalLight:
    """A directional (parallel-ray) light.

    Parameters
    ----------
    direction:
        The direction the light travels (a :class:`~pydex_ge.physics.Vector3`
        or a 3-element sequence).  Defaults to ``(0, -1, 0)`` (shining
        straight down).  The direction is normalized internally.
    color:
        The light RGB color (0-255 each).  Defaults to white.
    intensity:
        A float between 0 and 1 controlling brightness.  Defaults to ``1.0``.
    ambient:
        A float between 0 and 1 giving every lit surface a baseline
        brightness so faces pointing away from the light are dimmed but not
        pure black.  Defaults to ``0.0`` (no ambient, full contrast).
    enabled:
        Whether the light is active.  Defaults to ``True``.
    """

    __slots__ = ("_direction", "_color", "_intensity", "_ambient", "_enabled")

    def __init__(
        self,
        direction: object = (0, -1, 0),
        color: object = (255, 255, 255),
        intensity: object = 1.0,
        ambient: object = 0.0,
        enabled: bool = True,
    ) -> None:
        self._direction = self._as_direction(direction)
        self._color = normalize_rgb(color, "color")
        self._intensity = _intensity(intensity)
        self._ambient = _intensity(ambient)
        self._enabled = bool(enabled)

    @staticmethod
    def _as_direction(value: object) -> Vector3:
        if isinstance(value, Vector3):
            vector = value
        elif isinstance(value, (tuple, list)) and len(value) == 3:
            vector = Vector3(value[0], value[1], value[2])
        else:
            raise ConfigurationError(
                f"direction must be a Vector3 or a 3-element (x, y, z) sequence, got {value!r}."
            )
        if vector.length < 1e-9:
            raise ConfigurationError("direction must be non-zero.")
        return vector.normalized()

    @property
    def direction(self) -> Vector3:
        """The (normalized) light direction."""
        return self._direction

    @direction.setter
    def direction(self, value: object) -> None:
        self._direction = self._as_direction(value)

    @property
    def color(self) -> tuple[int, int, int]:
        """The light RGB color."""
        return self._color

    @color.setter
    def color(self, value: object) -> None:
        self._color = normalize_rgb(value, "color")

    @property
    def intensity(self) -> float:
        """The brightness between 0 and 1."""
        return self._intensity

    @intensity.setter
    def intensity(self, value: object) -> None:
        self._intensity = _intensity(value)

    @property
    def ambient(self) -> float:
        """The baseline brightness (0-1) applied to every lit surface."""
        return self._ambient

    @ambient.setter
    def ambient(self, value: object) -> None:
        self._ambient = _intensity(value)

    @property
    def enabled(self) -> bool:
        """Whether the light is active."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    def __repr__(self) -> str:
        return (
            f"DirectionalLight(direction={self._direction!r}, "
            f"color={self._color!r}, intensity={self._intensity!r}, "
            f"ambient={self._ambient!r})"
        )


__all__ = ["DirectionalLight"]
