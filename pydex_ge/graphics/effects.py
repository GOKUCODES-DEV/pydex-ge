"""Deterministic 2D effects: :class:`Fade`, :class:`Flash`, and :class:`Tint`.

These small helper objects advance purely from ``update(dt)`` — they never
sleep, never spawn threads, and never touch timers outside the normal game
loop.  The :class:`~pydex_ge.graphics.sprite.Sprite` uses them to implement
``sprite.fade_to(...)``, ``sprite.flash(...)``, and ``sprite.tint``.

All effects are deterministic: the same sequence of ``update(dt)`` calls
always produces the same result.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .color import normalize_rgb


def _alpha(value: object, name: str = "alpha") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
        raise ConfigurationError(f"{name} must be an int in 0-255, got {value!r}.")
    return value


def _positive_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if number <= 0:
        raise ConfigurationError(f"{name} must be greater than zero, got {value!r}.")
    return number


def _non_negative_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if number < 0:
        raise ConfigurationError(f"{name} must be non-negative, got {value!r}.")
    return number


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class Fade:
    """Gradually changes an alpha value from a start to a target over time.

    ``update(dt)`` returns the current alpha; when the duration has elapsed
    the alpha is exactly the target and :attr:`finished` is True.
    """

    def __init__(self, start_alpha: object, target_alpha: object, duration: object) -> None:
        self._start = _alpha(start_alpha, "start_alpha")
        self._target = _alpha(target_alpha, "target_alpha")
        self._duration = _positive_number(duration, "duration")
        self._time = 0.0

    def update(self, dt: object) -> int:
        """Advance the fade by ``dt`` seconds and return the current alpha."""
        dt = _non_negative_number(dt, "dt")
        self._time = min(self._duration, self._time + dt)
        return self.alpha

    @property
    def alpha(self) -> int:
        """The current interpolated alpha (0-255)."""
        if self.finished:
            return self._target
        t = self._time / self._duration
        return int(round(self._start + (self._target - self._start) * t))

    @property
    def start_alpha(self) -> int:
        """The alpha the fade started from."""
        return self._start

    @property
    def target_alpha(self) -> int:
        """The alpha the fade ends at."""
        return self._target

    @property
    def duration(self) -> float:
        """The fade duration in seconds."""
        return self._duration

    @property
    def time(self) -> float:
        """Seconds elapsed into the fade."""
        return self._time

    @property
    def progress(self) -> float:
        """How far through the fade we are (0.0 to 1.0)."""
        return _clamp(self._time / self._duration, 0.0, 1.0)

    @property
    def finished(self) -> bool:
        """True once the full duration has elapsed."""
        return self._time >= self._duration


class Flash:
    """A short white (or colored) flash that fades out over time.

    ``update(dt)`` advances the flash; :attr:`strength` starts at ``1.0``
    and decays to ``0.0``, at which point :attr:`finished` is True.  The
    color is the RGB value the affected sprite is tinted toward.
    """

    def __init__(self, duration: object, color: object = (255, 255, 255)) -> None:
        self._duration = _positive_number(duration, "duration")
        self._color = normalize_rgb(color, "color")
        self._time = 0.0

    def update(self, dt: object) -> float:
        """Advance the flash by ``dt`` seconds and return the current strength."""
        dt = _non_negative_number(dt, "dt")
        self._time = min(self._duration, self._time + dt)
        return self.strength

    @property
    def strength(self) -> float:
        """The current flash intensity, ``1.0`` at the start decaying to ``0.0``."""
        if self.finished:
            return 0.0
        return 1.0 - self._time / self._duration

    @property
    def color(self) -> tuple[int, int, int]:
        """The RGB color the flash tints the sprite toward."""
        return self._color

    @property
    def duration(self) -> float:
        """The flash duration in seconds."""
        return self._duration

    @property
    def time(self) -> float:
        """Seconds elapsed into the flash."""
        return self._time

    @property
    def finished(self) -> bool:
        """True once the full duration has elapsed."""
        return self._time >= self._duration


class Tint:
    """A validated RGB color multiply for a sprite (255 = no change).

    ``Tint((255, 255, 255))`` is the neutral tint; lowering a channel dims
    that color.  The stored value is always a normalized ``(r, g, b)``
    tuple with each channel an int in ``0-255``.
    """

    def __init__(self, color: object = (255, 255, 255)) -> None:
        self.color = color

    @property
    def color(self) -> tuple[int, int, int]:
        """The RGB tint as a validated ``(r, g, b)`` tuple."""
        return self._color

    @color.setter
    def color(self, value: object) -> None:
        self._color = normalize_rgb(value, "tint")

    @property
    def r(self) -> int:
        """The red channel (0-255)."""
        return self._color[0]

    @property
    def g(self) -> int:
        """The green channel (0-255)."""
        return self._color[1]

    @property
    def b(self) -> int:
        """The blue channel (0-255)."""
        return self._color[2]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tint):
            return NotImplemented
        return self._color == other._color

    def __repr__(self) -> str:
        return f"Tint({self._color!r})"


__all__ = ["Fade", "Flash", "Tint"]
