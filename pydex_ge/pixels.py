"""Tiny pure-stdlib image codecs (BMP, PNG) for the PYDEX tools.

The tools (editor, dexpen, dexview) avoid third-party imaging
dependencies, so this module provides just enough BMP and PNG support
on top of ``zlib``/``struct``.  Decoders return RGBA byte rows from the
top of the image down; encoders accept the same layout.

Only the subset product tools need is implemented, and malformed input
raises :class:`ValueError` with a clear message rather than crashing.
"""

from __future__ import annotations

import struct
import zlib

GRAY = 0
RGB = 2
RGBA = 6


class ImageCodecError(ValueError):
    """Raised for malformed or unsupported image data."""


def decode(image_bytes: bytes) -> tuple[int, int, list[bytes]]:
    """Decode a BMP or PNG into ``(width, height, rows)``.

    ``rows`` is a top-down list of ``width * 4`` byte strings in RGBA
    order.  The format is detected from the magic bytes.
    """
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ImageCodecError("Image data is empty.")
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return _decode_png(image_bytes)
    if image_bytes[:2] == b"BM":
        return _decode_bmp(image_bytes)
    raise ImageCodecError(
        "Unsupported image format (expected BMP or PNG)."
    )


def encode_bmp(
    width: int, height: int, rows: list[bytes]
) -> bytes:
    """Encode RGBA rows (top-down) as a 32-bit bottom-up BMP byte string."""
    _check_geometry(width, height, rows)
    row_size = width * 4
    padded = (row_size + 3) & ~3
    pixel_bytes = bytearray()
    for row in reversed(rows):
        line = bytearray(padded)
        for x in range(width):
            base = x * 4
            line[base] = row[base + 2]     # B
            line[base + 1] = row[base + 1]  # G
            line[base + 2] = row[base]      # R
            line[base + 3] = row[base + 3]  # A
        pixel_bytes += line
    header_size = 40
    data_size = len(pixel_bytes)
    file_size = 14 + header_size + data_size
    header = (
        b"BM"
        + struct.pack("<IHHI", file_size, 0, 0, 14 + header_size)
        + struct.pack(
            "<IiiHHIIiiII",
            header_size,
            width,
            height,
            1,
            32,
            0,
            data_size,
            2835,
            2835,
            0,
            0,
        )
    )
    return header + pixel_bytes


def encode_png(
    width: int, height: int, rows: list[bytes], *, color_type: int = RGBA
) -> bytes:
    """Encode RGBA rows (top-down) as a PNG byte string."""
    _check_geometry(width, height, rows)
    if color_type not in (RGB, RGBA):
        raise ImageCodecError("encode_png supports only RGB or RGBA.")
    channels = 4 if color_type == RGBA else 3
    raw = b"".join(
        b"\x00" + _row_to_channels(row, width, channels) for row in rows
    )
    ihdr = struct.pack(
        ">IIBBBBB", width, height, 8, color_type, 0, 0, 0
    )
    idat = zlib.compress(raw, 6)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", ihdr),
            _chunk(b"IDAT", idat),
            _chunk(b"IEND", b""),
        ]
    )


# -- decoding -----------------------------------------------------------


def _check_geometry(width: int, height: int, rows: list[bytes]) -> None:
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise ImageCodecError(f"Invalid image width: {width!r}.")
    if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
        raise ImageCodecError(f"Invalid image height: {height!r}.")
    if len(rows) != height:
        raise ImageCodecError(
            f"Expected {height} rows, got {len(rows)}."
        )
    for index, row in enumerate(rows):
        if len(row) != width * 4:
            raise ImageCodecError(
                f"Row {index} has {len(row)} bytes, expected {width * 4}."
            )


def _row_to_channels(
    row: bytes, width: int, channels: int
) -> bytes:
    out = bytearray(width * channels)
    for x in range(width):
        base = x * 4
        out[x * channels] = row[base]
        out[x * channels + 1] = row[base + 1]
        out[x * channels + 2] = row[base + 2]
        if channels == 4:
            out[x * channels + 3] = row[base + 3]
    return bytes(out)


def _decode_bmp(data: bytes) -> tuple[int, int, list[bytes]]:
    if len(data) < 14:
        raise ImageCodecError("BMP file is truncated (missing header).")
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    header_size = struct.unpack_from("<I", data, 14)[0]
    if header_size == 40 or header_size == 108 or header_size == 124:
        width, signed_height, planes, bpp = struct.unpack_from(
            "<iihH", data, 18
        )
        compression = struct.unpack_from("<I", data, 30)[0]
    elif header_size == 12:
        width, signed_height, planes, bpp = struct.unpack_from(
            "<HHHH", data, 18
        )
        compression = 0
    else:
        raise ImageCodecError(
            f"Unsupported BMP header size: {header_size}."
        )
    if width <= 0 or signed_height == 0:
        raise ImageCodecError("BMP has invalid dimensions.")
    top_down = signed_height < 0
    height = abs(signed_height)
    if planes != 1:
        raise ImageCodecError(f"BMP planes must be 1, got {planes}.")
    if compression != 0:
        raise ImageCodecError(
            f"Only uncompressed (BI_RGB) BMP is supported, got compression {compression}."
        )
    if bpp == 24:
        chars = 3
        row_w = width * 3
    elif bpp == 32:
        chars = 4
        row_w = width * 4
    elif bpp == 8:
        raise ImageCodecError("8-bit indexed BMP is not supported.")
    else:
        raise ImageCodecError(f"Unsupported BMP bit depth: {bpp}.")
    padded = (row_w + 3) & ~3
    end = pixel_offset + padded * height
    if end > len(data):
        raise ImageCodecError("BMP is truncated (pixel data missing).")
    rows: list[bytes] = []
    cursor = pixel_offset
    for _ in range(height):
        raw = data[cursor : cursor + padded]
        row = bytearray(width * 4)
        for x in range(width):
            base = x * chars
            row[x * 4] = raw[base + 2]
            row[x * 4 + 1] = raw[base + 1]
            row[x * 4 + 2] = raw[base]
            row[x * 4 + 3] = 255
        rows.append(bytes(row))
        cursor += padded
    if top_down:
        return width, height, rows
    return width, height, list(reversed(rows))


def _decode_png(data: bytes) -> tuple[int, int, list[bytes]]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ImageCodecError("Not a PNG file.")
    cursor = 8
    width = height = color_type = bit_depth = None
    sections: list[tuple[bytes, bytes]] = []
    while cursor + 8 <= len(data):
        length, name = struct.unpack_from(">I4s", data, cursor)
        cursor += 8
        if cursor + length + 4 > len(data):
            raise ImageCodecError("PNG chunk is truncated.")
        payload = data[cursor : cursor + length]
        sections.append((name, payload))
        cursor += length + 4
    for name, payload in sections:
        if name == b"IHDR":
            if len(payload) != 13:
                raise ImageCodecError("PNG IHDR is malformed.")
            width, height, bit_depth, color_type = struct.unpack_from(
                ">IIBB", payload, 0
            )
        elif name == b"IDAT":
            pass
    if not width or bit_depth != 8:
        raise ImageCodecError(
            f"Unsupported PNG: {width}x{height}, bit depth {bit_depth}."
        )
    if color_type not in (GRAY, RGB, RGBA):
        raise ImageCodecError(
            f"Unsupported PNG color type {color_type}."
        )
    channels = {GRAY: 1, RGB: 3, RGBA: 4}[color_type]
    compressed = b"".join(
        payload for name, payload in sections if name == b"IDAT"
    )
    if not compressed:
        raise ImageCodecError("PNG has no image data.")
    raw = zlib.decompress(compressed)
    expect = (width * channels + 1) * height
    if len(raw) < expect:
        raise ImageCodecError("PNG image data is truncated.")
    rows = _unfilter(raw, width, height, channels)
    out: list[bytes] = []
    for row in rows:
        rgba = bytearray(width * 4)
        for x in range(width):
            base = x * channels
            rgba[x * 4] = row[base]
            rgba[x * 4 + 1] = row[base + 1] if channels >= 3 else row[base]
            rgba[x * 4 + 2] = row[base + 2] if channels >= 3 else row[base]
            rgba[x * 4 + 3] = row[base + 3] if channels == 4 else 255
        out.append(bytes(rgba))
    return width, height, out


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(
    raw: bytes, width: int, height: int, channels: int
) -> list[bytes]:
    stride = width * channels
    rows: list[bytearray] = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        if filter_type == 0:
            pass
        elif filter_type == 1:
            for x in range(channels, stride):
                row[x] = (row[x] + row[x - channels]) & 0xFF
        elif filter_type == 2:
            for x in range(stride):
                row[x] = (row[x] + previous[x]) & 0xFF
        elif filter_type == 3:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                row[x] = (row[x] + ((left + previous[x]) >> 1)) & 0xFF
        elif filter_type == 4:
            for x in range(stride):
                a = row[x - channels] if x >= channels else 0
                b = previous[x]
                c = previous[x - channels] if x >= channels else 0
                row[x] = (row[x] + _paeth(a, b, c)) & 0xFF
        else:
            raise ImageCodecError(f"Unknown PNG filter type {filter_type}.")
        rows.append(row)
        previous = row
    return [bytes(row) for row in rows]


def _chunk(name: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + name
        + payload
        + struct.pack(">I", zlib.crc32(name + payload) & 0xFFFFFFFF)
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