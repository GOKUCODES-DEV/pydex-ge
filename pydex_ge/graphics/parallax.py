"""Parallax backgrounds: sprites that move slower than the world.

A :class:`Parallax` wraps a :class:`~pydex_ge.graphics.sprite.Sprite` and a
``factor``:

* ``factor=1.0`` draws the sprite exactly like a normal world object,
* ``factor=0.0`` keeps it fixed to the screen (a pure UI background),
* values in between scroll it at a fraction of the camera's speed.

Parallax uses the renderer's *active camera* (the camera currently
between ``begin_camera``/``end_camera``) to compute the offset, so the
calculation is **visual only**: the sprite's stored world position is
never changed and any temporary state is restored after drawing.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .sprite import Sprite


def _factor_pair(value: object) -> tuple[float, float]:
    """Normalize a parallax factor (a number or an ``(x, y)`` pair)."""
    if isinstance(value, (tuple, list)):
        if len(value) != 2:
            raise ConfigurationError(
                f"factor must be a number or a 2-element (x, y) pair, got {value!r}."
            )
        fx, fy = value[0], value[1]
    else:
        fx = fy = value
    return _factor(fx, "factor"), _factor(fy, "factor")


def _factor(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    return float(value)


class Parallax:
    """A sprite scrolled at a fraction of the camera's speed.

    Parameters
    ----------
    sprite:
        The :class:`~pydex_ge.graphics.sprite.Sprite` to draw.
    factor:
        The parallax factor: ``1.0`` = normal world movement, ``0.0`` =
        screen-fixed, or an ``(x, y)`` pair for per-axis scrolling.
    """

    def __init__(self, sprite: object, factor: object = 0.25) -> None:
        if not isinstance(sprite, Sprite):
            raise ConfigurationError("Parallax requires a pydex_ge.Sprite.")
        self.sprite = sprite
        self._factor_x, self._factor_y = _factor_pair(factor)

    @property
    def factor(self) -> float | tuple[float, float]:
        """The parallax factor (``1.0`` normal, ``0.0`` screen-fixed)."""
        if abs(self._factor_x - self._factor_y) < 1e-9:
            return self._factor_x
        return (self._factor_x, self._factor_y)

    @factor.setter
    def factor(self, value: object) -> None:
        self._factor_x, self._factor_y = _factor_pair(value)

    @property
    def factor_x(self) -> float:
        """The horizontal parallax factor."""
        return self._factor_x

    @factor_x.setter
    def factor_x(self, value: object) -> None:
        self._factor_x = _factor(value, "factor_x")

    @property
    def factor_y(self) -> float:
        """The vertical parallax factor."""
        return self._factor_y

    @factor_y.setter
    def factor_y(self, value: object) -> None:
        self._factor_y = _factor(value, "factor_y")

    def offset(self, camera) -> tuple[float, float]:
        """The visual ``(dx, dy)`` offset for the current camera position.

        ``factor=1.0`` gives ``(0, 0)`` (no offset, normal movement);
        ``factor=0.0`` gives the full camera position (screen-fixed).
        """
        if camera is None:
            return (0.0, 0.0)
        return (
            camera.position.x * (1.0 - self._factor_x),
            camera.position.y * (1.0 - self._factor_y),
        )

    def draw(self, renderer) -> None:
        """Draw the parallax sprite, offsetting only the drawn position.

        The sprite's stored position is restored in a ``finally`` block, so
        this method never changes the sprite's world position.
        """
        camera = renderer.active_camera
        dx, dy = self.offset(camera)
        if dx == 0.0 and dy == 0.0:
            self.sprite.draw(renderer)
            return
        original = (self.sprite.x, self.sprite.y)
        try:
            self.sprite.x = int(round(self.sprite.x + dx))
            self.sprite.y = int(round(self.sprite.y + dy))
            self.sprite.draw(renderer)
        finally:
            self.sprite.x, self.sprite.y = original

    def __repr__(self) -> str:
        return f"Parallax(sprite={self.sprite!r}, factor={self.factor!r})"


__all__ = ["Parallax"]
