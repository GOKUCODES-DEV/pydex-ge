"""Color handling for the PYDEX graphics system.

PYDEX colors are simple tuples of integers.  Users never deal with SDL
color structures; those are produced internally by the helpers below.
"""
from __future__ import annotations

from ..exceptions import ConfigurationError


def _normalize(color: object, name: str, length: int) -> tuple[int, ...]:
    if not isinstance(color, (tuple, list)) or len(color) != length:
        raise ConfigurationError(
            f"{name} must be a {'RGBA' if length == 4 else 'RGB'} tuple of "
            f"{length} ints, got {color!r}."
        )
    channels = []
    for index, channel in enumerate(color):
        if isinstance(channel, bool) or not isinstance(channel, int):
            raise ConfigurationError(
                f"{name} channel {index} must be an int, got {channel!r}."
            )
        if not 0 <= channel <= 255:
            raise ConfigurationError(
                f"{name} channel {index} out of range 0-255: {channel!r}."
            )
        channels.append(channel)
    return tuple(channels)


def normalize_rgb(color: object, name: str = "color") -> tuple[int, int, int]:
    """Validate an RGB value and return it as three ints in the 0-255 range."""
    r, g, b = _normalize(color, name, 3)
    return r, g, b


def normalize_rgba(
    color: object, name: str = "color"
) -> tuple[int, int, int, int]:
    """Validate an RGB or RGBA value and return RGBA ints in the 0-255 range.

    A three-element RGB value gets an implicit alpha of 255.
    """
    if isinstance(color, (tuple, list)) and len(color) == 3:
        r, g, b = _normalize(color, name, 3)
        return r, g, b, 255
    return _normalize(color, name, 4)


__all__ = ["normalize_rgb", "normalize_rgba"]