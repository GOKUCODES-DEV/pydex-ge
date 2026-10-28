"""Shared stdlib-only runtime asset generator for the PYDEX field-test games.

Every game writes its own PNG sheets and WAV clips into a private temp
directory (never committed to the repo), so the demos need no asset files.
These helpers produce RGBA PNG bytes and 16-bit mono WAV bytes using the
standard library alone.
"""

from __future__ import annotations

import io
import math
import struct
import wave
import zlib

Color = tuple[int, int, int, int]

# -- PNG ------------------------------------------------------------------


def png_bytes(width: int, height: int, rows: list[bytes]) -> bytes:
    """Encode RGBA ``rows`` (top-down, ``width * 4`` bytes each) as PNG bytes."""
    def _chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    scanlines = b"".join(b"\x00" + row for row in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(scanlines))
        + _chunk(b"IEND", b"")
    )


def blank(size: int) -> list[list[Color]]:
    """A transparent ``size`` x ``size`` RGBA cell to stamp art into."""
    return [[(0, 0, 0, 0)] * size for _ in range(size)]


def stamp(cell, x: int, y: int, w: int, h: int, color: Color) -> None:
    """Fill a rectangle of ``cell`` with ``color`` (clipped to the cell)."""
    for row in range(y, y + h):
        for col in range(x, x + w):
            if 0 <= row < len(cell) and 0 <= col < len(cell[0]):
                cell[row][col] = color


def cell_rows(cell) -> list[bytes]:
    """Convert a 2D RGBA cell into one RGBA byte string per row."""
    rows: list[bytes] = []
    for row in range(len(cell)):
        line = bytearray()
        for col in range(len(cell[row])):
            line += bytes(cell[row][col])
        rows.append(bytes(line))
    return rows


def sheet_png(cells, size: int = 16) -> bytes:
    """Encode a horizontal strip of ``size`` x ``size`` ``cells`` as one PNG."""
    rows: list[bytes] = []
    for row in range(size):
        line = bytearray()
        for cell in cells:
            for col in range(size):
                line += bytes(cell[row][col])
        rows.append(bytes(line))
    return png_bytes(size * len(cells), size, rows)


def solid_pixels(width: int, height: int, color) -> bytes:
    """A ``width`` x ``height`` solid RGBA pixel block."""
    row = bytes((*color, 255)) * width
    return row * height


# -- WAV ------------------------------------------------------------------


def tone(
    freq: float,
    seconds: float,
    rate: int = 22050,
    volume: float = 0.7,
    decay: bool = True,
) -> list[int]:
    """A short sine tone as 16-bit samples (``-32768..32767``)."""
    n = int(rate * seconds)
    if n <= 0:
        return []
    return [
        int(
            volume
            * (1.0 - i / n if decay else 1.0)
            * 32767
            * math.sin(2 * math.pi * freq * i / rate)
        )
        for i in range(n)
    ]


def melody(notes, rate: int = 22050, volume: float = 0.65) -> list[int]:
    """Concatenate ``notes`` (freq, seconds) pairs into one decaying tune."""
    samples: list[int] = []
    for freq, seconds in notes:
        samples += tone(freq, seconds, rate=rate, volume=volume, decay=True)
    return samples


def wav_bytes(samples, rate: int = 22050) -> bytes:
    """Encode 16-bit mono samples as WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(
            b"".join(
                struct.pack("<h", int(max(-32767, min(32767, sample))))
                for sample in samples
            )
        )
    return buf.getvalue()


__all__ = [
    "blank",
    "cell_rows",
    "melody",
    "png_bytes",
    "sheet_png",
    "solid_pixels",
    "stamp",
    "tone",
    "wav_bytes",
]