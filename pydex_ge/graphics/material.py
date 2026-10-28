"""The :class:`Material`: surface properties applied to a mesh.

A material holds a base color, an opacity, an optional texture reference
and an optional emissive color.  The 3D renderer multiplies the base color
by the directional light before drawing, so a fully dark material appears
black unless it emits light.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .color import normalize_rgb


def _opacity(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"opacity must be a number between 0 and 1, got {value!r}.")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ConfigurationError(f"opacity must be a number between 0 and 1, got {value!r}.")
    return number


class Material:
    """A surface description for 3D objects.

    Parameters
    ----------
    color:
        The base RGB color (0-255 each).  Defaults to white.
    opacity:
        A float between 0 and 1 (fully transparent to fully opaque).
        Defaults to ``1.0``.
    texture:
        An optional :class:`~pydex_ge.graphics.Image` reference.  Textures are
        not applied by the CPU renderer yet, but keeping the reference lets
        materials stay forward-compatible.
    emission:
        Optional RGB color added on top of the lit result, for glowing
        materials.  Defaults to ``(0, 0, 0)`` (no emission).
    """

    __slots__ = ("_color", "_opacity", "_texture", "_emission")

    def __init__(
        self,
        color: object = (255, 255, 255),
        opacity: object = 1.0,
        texture: object = None,
        emission: object = (0, 0, 0),
    ) -> None:
        self._color = normalize_rgb(color, "color")
        self._opacity = _opacity(opacity)
        self._texture = texture
        self._emission = normalize_rgb(emission, "emission")

    @property
    def color(self) -> tuple[int, int, int]:
        """The base RGB color."""
        return self._color

    @color.setter
    def color(self, value: object) -> None:
        self._color = normalize_rgb(value, "color")

    @property
    def opacity(self) -> float:
        """The opacity between 0 and 1."""
        return self._opacity

    @opacity.setter
    def opacity(self, value: object) -> None:
        self._opacity = _opacity(value)

    @property
    def texture(self) -> object | None:
        """The optional :class:`~pydex_ge.graphics.Image` texture reference."""
        return self._texture

    @texture.setter
    def texture(self, value: object) -> None:
        self._texture = value

    @property
    def emission(self) -> tuple[int, int, int]:
        """The emissive RGB color added on top of the lit result."""
        return self._emission

    @emission.setter
    def emission(self, value: object) -> None:
        self._emission = normalize_rgb(value, "emission")

    def copy(self) -> Material:
        """A new material with the same values (the texture reference is shared)."""
        return Material(
            color=self._color,
            opacity=self._opacity,
            texture=self._texture,
            emission=self._emission,
        )

    def __repr__(self) -> str:
        return (
            f"Material(color={self._color!r}, opacity={self._opacity!r}, "
            f"emission={self._emission!r})"
        )


__all__ = ["Material"]
