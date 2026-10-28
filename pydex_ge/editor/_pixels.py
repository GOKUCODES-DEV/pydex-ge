"""Pixel codecs for the editor (shared engine lives in :mod:`pydex_ge.pixels`).

Kept as a named module so existing imports/tests keep working; the
implementation moved to ``pydex_ge.pixels`` so dexpen and other tools can
reuse it without importing the editor.
"""

from __future__ import annotations

from ..pixels import (
    GRAY,
    RGB,
    RGBA,
    ImageCodecError,
    decode,
    encode_bmp,
    encode_png,
)

__all__ = [
    "decode",
    "encode_bmp",
    "encode_png",
    "ImageCodecError",
    "GRAY",
    "RGB",
    "RGBA",
]