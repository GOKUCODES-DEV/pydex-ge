"""Helpers that synthesize tiny PNG/JPG/BMP images for headless tests.

Only the file *structure* matters to the null backend (it reads dimensions
from the headers), so these need no external image library.  The SDL2
backend tests reuse the same PNG/BMP files to verify real decoding.
"""

from __future__ import annotations

import struct
import zlib

BMP_MAGIC = b"BM"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOFT_START = b"\xff\xd8"


def bmp_bytes(width: int, height: int) -> bytes:
    row_size = (width * 3 + 3) // 4 * 4
    data_size = row_size * height
    file_header = struct.pack("<2sIHHI", BMP_MAGIC, 14 + 40 + data_size, 0, 0, 14 + 40)
    dib_header = struct.pack(
        "<IiiHHIIiiII", 40, width, height, 1, 24, 0, data_size, 0, 0, 0, 0
    )
    pixels = b"\x00" * data_size
    return file_header + dib_header + pixels


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png_bytes(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    scanlines = b"".join(b"\x00" + bytes(width * 4) for _ in range(height))
    idat = zlib.compress(scanlines)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def jpeg_bytes(width: int, height: int) -> bytes:
    app0 = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0_payload = (
        b"\x08"
        + struct.pack(">HH", height, width)
        + b"\x01\x01\x01\x00"
    )
    return (
        JPEG_SOFT_START
        + b"\xff\xe0"
        + struct.pack(">H", 2 + len(app0))
        + app0
        + b"\xff\xc0"
        + struct.pack(">H", 2 + len(sof0_payload))
        + sof0_payload
        + b"\xff\xd9"
    )


def write_fixture(directory: str, name: str, data: bytes) -> str:
    import os

    path = os.path.join(directory, name)
    with open(path, "wb") as handle:
        handle.write(data)
    return path