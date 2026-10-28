"""The :class:`Label`: a friendly text renderable.

A :class:`Label` is a :class:`~pydex_ge.graphics.text.Text` with a convenient
beginner-friendly API: you can create one with just a string and a
position, change its text at runtime, and it draws with whatever font was
given (or a system fallback).
"""

from __future__ import annotations

from .text import Text


class Label(Text):
    """A simple, positionable piece of text.

    ``pydex_ge.Label("Hello PYDEX", position=(100, 100))`` is all you need to
    draw text.  Setting :attr:`text` updates what is rendered on the next
    frame.

    Parameters
    ----------
    text:
        The string to display.
    position:
        Top-left ``(x, y)`` in pixels.
    font:
        A :class:`~pydex_ge.graphics.font.Font`, a font file path, or ``None``
        for a system font.  A :class:`Font` instance is shared and never
        destroyed by this label.
    font_size:
        Point size when a font is created internally.
    color:
        RGB or RGBA tuple, each channel 0-255.
    visible:
        Whether the label is drawn.
    """


__all__ = ["Label"]
