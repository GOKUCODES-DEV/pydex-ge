"""Canvas model for dexpen: an RGBA pixel grid with undo/redo and codecs.

The model is backend-agnostic: it just owns ``width * height * 4`` bytes.
Save/load reuse the ``pydex_ge.editor`` pixel codec (BMP/PNG).
"""

from __future__ import annotations

import os

from .. import pixels as _pixels
from ..exceptions import ConfigurationError

_MAX_HISTORY = 128


def _rgba(color) -> tuple[int, int, int, int]:
    if isinstance(color, (list, tuple)):
        if len(color) == 3:
            r, g, b = color
            return (int(r), int(g), int(b), 255)
        if len(color) == 4:
            r, g, b, a = color
            return (int(r), int(g), int(b), int(a))
    raise ConfigurationError(f"Color must be an RGB/RGBA tuple, got {color!r}.")


class Canvas:
    """A width-by-height grid of RGBA pixels."""

    def __init__(self, width: int = 32, height: int = 32, *, color=(0, 0, 0, 255)) -> None:
        width = _dimension(width, "width")
        height = _dimension(height, "height")
        self.width = width
        self.height = height
        self._buf = bytearray(width * height * 4)
        self._undo: list[bytes] = []
        self._redo: list[bytes] = []
        self._stroke_base: bytes | None = None
        self.clear(color)

    # -- pixels ---------------------------------------------------------------

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _index(self, x: int, y: int) -> int:
        return (y * self.width + x) * 4

    def get(self, x: int, y: int) -> tuple[int, int, int, int]:
        if not self.in_bounds(x, y):
            raise IndexError(f"({x}, {y}) is outside a {self.width}x{self.height} canvas.")
        i = self._index(x, y)
        return tuple(self._buf[i : i + 4])  # type: ignore[return-value]

    def set(self, x: int, y: int, color) -> None:
        if not self.in_bounds(x, y):
            return
        r, g, b, a = _rgba(color)
        i = self._index(x, y)
        self._buf[i : i + 4] = bytes((r, g, b, a))

    def clear(self, color=(0, 0, 0, 255)) -> None:
        r, g, b, a = _rgba(color)
        self._buf[:] = bytes((r, g, b, a)) * (self.width * self.height)  # type: ignore[arg-type]

    # -- undo / redo ------------------------------------------------------------

    def begin(self) -> None:
        """Record a baseline; call once before a stroke, then ``commit()``."""
        self._stroke_base = bytes(self._buf)

    def commit(self) -> None:
        """Push the pre-stroke baseline onto undo history (if anything changed)."""
        if self._stroke_base is None:
            return
        if self._stroke_base != bytes(self._buf):
            self._undo.append(self._stroke_base)
            if len(self._undo) > _MAX_HISTORY:
                self._undo.pop(0)
        self._redo.clear()
        self._stroke_base = None

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(bytes(self._buf))
        self._buf[:] = self._undo.pop()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(bytes(self._buf))
        self._buf[:] = self._redo.pop()
        return True

    # -- drawing helpers ----------------------------------------------------------

    def paint(self, cells, color) -> None:
        r, g, b, a = _rgba(color)
        seen: set[tuple[int, int]] = set()
        for cx, cy in cells:
            if not self.in_bounds(cx, cy):
                continue
            key = (cx, cy)
            if key in seen:
                continue
            seen.add(key)
            i = self._index(cx, cy)
            self._buf[i : i + 4] = bytes((r, g, b, a))

    def flood_fill(self, x: int, y: int, color) -> None:
        if not self.in_bounds(x, y):
            return
        r, g, b, a = _rgba(color)
        target = self.get(x, y)
        if target == (r, g, b, a):
            return
        start = (x, y)
        self._buf[self._index(x, y) : self._index(x, y) + 4] = bytes((r, g, b, a))
        stack = [start]
        while stack:
            cx, cy = stack.pop()
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if not self.in_bounds(nx, ny):
                    continue
                if self.get(nx, ny) != target:
                    continue
                i = self._index(nx, ny)
                self._buf[i : i + 4] = bytes((r, g, b, a))
                stack.append((nx, ny))

    @staticmethod
    def line_cells(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
        """Bresenham cells between two grid points (inclusive)."""
        cells: list[tuple[int, int]] = []
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            cells.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return cells

    @staticmethod
    def rect_cells(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
        """Edge cells of a rectangle (outline only)."""
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        cells: list[tuple[int, int]] = []
        for x in range(left, right + 1):
            cells.append((x, top))
            if bottom != top:
                cells.append((x, bottom))
        for y in range(top + 1, bottom):
            cells.append((left, y))
            if right != left:
                cells.append((right, y))
        return cells

    def line(self, x0: int, y0: int, x1: int, y1: int, color) -> None:
        self.paint(self.line_cells(x0, y0, x1, y1), color)

    def rect(self, x0: int, y0: int, x1: int, y1: int, color, *, filled: bool = True) -> None:
        cells = self.rect_cells(x0, y0, x1, y1)
        if filled:
            left, right = sorted((x0, x1))
            top, bottom = sorted((y0, y1))
            all_cells = [(x, y) for x in range(left, right + 1) for y in range(top, bottom + 1)]
            cells = all_cells
        self.paint(cells, color)

    # -- serialization -----------------------------------------------------------

    def to_rows(self) -> list[bytes]:
        rows: list[bytes] = []
        stride = self.width * 4
        for y in range(self.height):
            i = y * stride
            rows.append(bytes(self._buf[i : i + stride]))
        return rows

    def from_rows(self, width: int, height: int, rows) -> None:
        if width < 1 or height < 1:
            raise ConfigurationError("Width and height must be positive.")
        from_pixels(rows, height, width * 4)
        self.width = width
        self.height = height
        buf = bytearray()
        for row in rows:
            buf.extend(row)
        if len(buf) != width * height * 4:
            raise _pixels.ImageCodecError("Row data does not match canvas dimensions.")
        self._buf[:] = buf
        self._undo.clear()
        self._redo.clear()
        self._stroke_base = None

    def encode_png(self) -> bytes:
        return _pixels.encode_png(self.width, self.height, self.to_rows())

    def encode_bmp(self) -> bytes:
        return _pixels.encode_bmp(self.width, self.height, self.to_rows())

    def save(self, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()
        data = self.encode_bmp() if ext == ".bmp" else self.encode_png()
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)

    @classmethod
    def load(cls, path: str) -> Canvas:
        with open(path, "rb") as handle:
            data = handle.read()
        width, height, rows = _pixels.decode(data)
        canvas = cls(width, height)
        canvas.from_rows(width, height, rows)
        return canvas


def _dimension(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigurationError(f"{name} must be a positive integer, got {value!r}.")
    return value


def from_pixels(rows, expected_height: int, row_length: int) -> None:
    if len(rows) != expected_height:
        raise _pixels.ImageCodecError(
            f"Expected {expected_height} rows, got {len(rows)}."
        )
    for row in rows:
        if len(row) != row_length:
            raise _pixels.ImageCodecError(
                f"Row width {len(row)} != expected {row_length} bytes."
            )


__all__ = ["Canvas"]