"""The :class:`TileMap`: a grid of sprites with culled rendering and collision.

A :class:`TileMap` is a ``width`` by ``height`` grid of tile IDs drawn from
a :class:`~pydex_ge.graphics.sprite_sheet.SpriteSheet`.  Tile ID ``0`` is
empty; ``1`` is the first sheet cell, ``2`` the second, and so on
(row-major through the sheet's cells).

Rendering is camera-aware: only tiles inside the visible viewport are
drawn.  Solid tiles can be merged into horizontal runs for cheap collision
with :class:`~pydex_ge.physics.body.Body` through the existing static-rectangle
system.
"""

from __future__ import annotations

import math

from ..exceptions import ConfigurationError
from ..graphics.sprite_sheet import SpriteSheet
from ..physics.rect import Rect


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer, got {value!r}.")
    return value


def _non_negative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"{name} must be a non-negative integer, got {value!r}.")
    return value


def _tile_size(value: object) -> tuple[int, int]:
    if isinstance(value, (tuple, list)):
        if len(value) != 2:
            raise ConfigurationError(
                f"tile_size must be an (width, height) pair, got {value!r}."
            )
        return _positive_int(value[0], "tile_width"), _positive_int(value[1], "tile_height")
    raise ConfigurationError(
        f"tile_size must be an (width, height) pair, got {value!r}."
    )


class TileMap:
    """A camera-culled grid of tiles from a sprite sheet.

    Parameters
    ----------
    width, height:
        The number of columns and rows of tiles.  Both must be positive.
    tile_size:
        The ``(tile_width, tile_height)`` in pixels (default ``(32, 32)``).
    tiles:
        An optional 2D list of rows (each row a list of tile IDs) matching
        ``width`` x ``height``.  When omitted the map starts empty.
    sprite_sheet:
        An optional :class:`~pydex_ge.graphics.sprite_sheet.SpriteSheet` used
        to draw tiles.  Tile ID ``1`` is the sheet's first cell, ``2`` the
        second, and so on (row-major).

    Example
    -------
    ::

        tiles = pydex_ge.TileMap(20, 15, tile_size=(32, 32))
        tiles.sprite_sheet = pydex_ge.SpriteSheet(image, 32, 32)
        tiles.set_tile(3, 4, 1)      # draw the first cell here
        tiles.set_solid(1, True)     # tile 1 blocks the player
        tiles.render(renderer, camera)
    """

    def __init__(
        self,
        width: object,
        height: object,
        tile_size: object = (32, 32),
        tiles=None,
        *,
        sprite_sheet: object = None,
    ) -> None:
        self._width = _positive_int(width, "width")
        self._height = _positive_int(height, "height")
        self._tile_width, self._tile_height = _tile_size(tile_size)
        self._grid = [0] * (self._width * self._height)
        self._solid: dict[int, bool] = {}
        self._sprite_sheet = None
        self._cell_sprites = {}

        self.sprite_sheet = sprite_sheet
        if tiles is not None:
            self._load_tiles(tiles)

    def _load_tiles(self, tiles) -> None:
        if isinstance(tiles, (str, bytes)) or not hasattr(tiles, "__iter__"):
            raise ConfigurationError(
                "tiles must be a 2D list of rows, each a list of tile IDs."
            )
        rows = list(tiles)
        if len(rows) != self._height:
            raise ConfigurationError(
                f"tiles has {len(rows)} rows but the map is {self._height} high."
            )
        for row_index, row in enumerate(rows):
            if isinstance(row, (str, bytes)) or not hasattr(row, "__iter__"):
                raise ConfigurationError(
                    f"tiles row {row_index} must be a list of tile IDs."
                )
            row = list(row)
            if len(row) != self._width:
                raise ConfigurationError(
                    f"tiles row {row_index} has {len(row)} columns but the map "
                    f"is {self._width} wide."
                )
            for col, tile_id in enumerate(row):
                if tile_id is None:
                    tile_id = 0
                self._grid[row_index * self._width + col] = _non_negative_int(
                    tile_id, "tile_id"
                )

    # -- dimensions --------------------------------------------------------

    @property
    def width(self) -> int:
        """The number of tile columns."""
        return self._width

    @property
    def height(self) -> int:
        """The number of tile rows."""
        return self._height

    @property
    def cols(self) -> int:
        """Alias for :attr:`width` (number of tile columns)."""
        return self._width

    @property
    def rows(self) -> int:
        """Alias for :attr:`height` (number of tile rows)."""
        return self._height

    @property
    def tile_width(self) -> int:
        """The width of one tile in pixels."""
        return self._tile_width

    @property
    def tile_height(self) -> int:
        """The height of one tile in pixels."""
        return self._tile_height

    @property
    def tile_size(self) -> tuple[int, int]:
        """The ``(tile_width, tile_height)`` in pixels."""
        return (self._tile_width, self._tile_height)

    @property
    def pixel_width(self) -> int:
        """The map width in pixels (``cols * tile_width``)."""
        return self._width * self._tile_width

    @property
    def pixel_height(self) -> int:
        """The map height in pixels (``rows * tile_height``)."""
        return self._height * self._tile_height

    # -- tiles -------------------------------------------------------------

    def set_tile(self, col: object, row: object, tile_id: object) -> None:
        """Set the tile at ``(col, row)`` to ``tile_id`` (``0`` = empty)."""
        col = self._check_cell(col, row)
        tile_id = _non_negative_int(tile_id, "tile_id")
        self._grid[row * self._width + col] = tile_id

    def get_tile(self, col: object, row: object) -> int:
        """Return the tile ID at ``(col, row)`` (``0`` = empty)."""
        col = self._check_cell(col, row)
        return self._grid[row * self._width + col]

    def clear(self) -> None:
        """Set every tile back to ``0`` (empty)."""
        self._grid = [0] * (self._width * self._height)

    def _check_cell(self, col: object, row: object) -> int:
        col = _non_negative_int(col, "col")
        row = _non_negative_int(row, "row")
        if col >= self._width or row >= self._height:
            raise ConfigurationError(
                f"tile ({col}, {row}) is outside the {self._width}x{self._height} map."
            )
        return col

    def tile_rect(self, col: object, row: object) -> Rect:
        """The world-space rectangle of the tile at ``(col, row)``."""
        col = self._check_cell(col, row)
        return Rect(
            col * self._tile_width,
            row * self._tile_height,
            self._tile_width,
            self._tile_height,
        )

    def tile_at(self, world_x: object, world_y: object) -> tuple[int, int] | None:
        """The ``(col, row)`` under a world point, or None when outside the map."""
        if isinstance(world_x, bool) or not isinstance(world_x, (int, float)):
            raise ConfigurationError(f"world_x must be a number, got {world_x!r}.")
        if isinstance(world_y, bool) or not isinstance(world_y, (int, float)):
            raise ConfigurationError(f"world_y must be a number, got {world_y!r}.")
        col = math.floor(float(world_x) / self._tile_width)
        row = math.floor(float(world_y) / self._tile_height)
        if col < 0 or row < 0 or col >= self._width or row >= self._height:
            return None
        return (col, row)

    # -- sprite sheet ------------------------------------------------------

    @property
    def sprite_sheet(self):
        """The :class:`~pydex_ge.graphics.sprite_sheet.SpriteSheet` tiles are drawn from."""
        return self._sprite_sheet

    @sprite_sheet.setter
    def sprite_sheet(self, value: object) -> None:
        if value is not None and not isinstance(value, SpriteSheet):
            raise ConfigurationError("sprite_sheet must be a pydex_ge.SpriteSheet or None.")
        self._sprite_sheet = value
        self._cell_sprites.clear()

    def _cell_sprite(self, tile_id: int):
        sheet = self._sprite_sheet
        if sheet is None:
            raise ConfigurationError(
                "TileMap needs a sprite_sheet before it can draw tiles."
            )
        if sheet.cell_width is None or sheet.cell_height is None:
            raise ConfigurationError(
                "The TileMap sprite_sheet needs cell_width and cell_height."
            )
        if tile_id <= 0:
            raise ConfigurationError(
                "Tile IDs start at 1 (the sprite sheet's first cell); 0 means "
                "an empty tile and cannot be drawn."
            )
        cached = self._cell_sprites.get(tile_id)
        if cached is not None:
            return cached
        if sheet.columns is None or sheet.columns == 0:
            raise ConfigurationError("The TileMap sprite_sheet has no usable cells.")
        cell_index = tile_id - 1
        column = cell_index % sheet.columns
        row = cell_index // sheet.columns
        sprite = sheet.cell(column, row)
        self._cell_sprites[tile_id] = sprite
        return sprite

    # -- collision ---------------------------------------------------------

    def set_solid(self, tile_id: object, solid: object = True) -> None:
        """Mark ``tile_id`` as solid (collidable) or not."""
        tile_id = _non_negative_int(tile_id, "tile_id")
        if not isinstance(solid, bool):
            raise ConfigurationError("solid must be a bool.")
        if solid:
            self._solid[tile_id] = True
        else:
            self._solid.pop(tile_id, None)

    def is_solid(self, tile_id: object) -> bool:
        """True when ``tile_id`` is marked solid."""
        tile_id = _non_negative_int(tile_id, "tile_id")
        return self._solid.get(tile_id, False)

    def solid_rects(self) -> list[Rect]:
        """World rectangles for solid tiles, merging horizontal runs.

        Adjacent solid tiles in the same row are merged into one wider
        rectangle so collision resolution stays fast and feels stable.
        """
        rects: list[Rect] = []
        for row in range(self._height):
            col = 0
            while col < self._width:
                if self.is_solid(self._grid[row * self._width + col]):
                    start = col
                    while (
                        col < self._width
                        and self.is_solid(self._grid[row * self._width + col])
                    ):
                        col += 1
                    rects.append(
                        Rect(
                            start * self._tile_width,
                            row * self._tile_height,
                            (col - start) * self._tile_width,
                            self._tile_height,
                        )
                    )
                else:
                    col += 1
        return rects

    def collide_body(self, body) -> bool:
        """Resolve ``body`` against every solid tile.

        Reuses :meth:`pydex_ge.physics.Body.collide_static` for each merged
        solid rectangle.  Returns True when at least one collision was
        resolved.
        """
        resolved = False
        for rect in self.solid_rects():
            if body.collide_static(rect):
                resolved = True
        return resolved

    # -- rendering ---------------------------------------------------------

    def render(self, renderer, camera=None) -> None:
        """Draw every tile visible through ``camera``.

        When ``camera`` is None the renderer's active camera (if any) is
        used; with no camera at all every tile is drawn.  Tiles outside the
        visible viewport are skipped.
        """
        if self._sprite_sheet is None:
            return
        camera = camera if camera is not None else renderer.active_camera

        if camera is None:
            col_start, col_end = 0, self._width
            row_start, row_end = 0, self._height
        elif hasattr(camera, "screen_to_world") and camera.width is not None and camera.height is not None:
            top_left = camera.screen_to_world((0, 0))
            bottom_right = camera.screen_to_world((camera.width, camera.height))
            col_start = self._clamp_col(math.floor(top_left.x / self._tile_width))
            col_end = self._clamp_col(math.ceil(bottom_right.x / self._tile_width))
            row_start = self._clamp_row(math.floor(top_left.y / self._tile_height))
            row_end = self._clamp_row(math.ceil(bottom_right.y / self._tile_height))
        else:
            # A Camera3D (or a camera with no viewport) cannot be used for
            # 2D tile culling; draw every tile instead of crashing.
            col_start, col_end = 0, self._width
            row_start, row_end = 0, self._height

        for row in range(row_start, row_end):
            for col in range(col_start, col_end):
                tile_id = self._grid[row * self._width + col]
                if tile_id == 0:
                    continue
                sprite = self._cell_sprite(tile_id)
                sprite.x = col * self._tile_width
                sprite.y = row * self._tile_height
                sprite.scale_x = self._tile_width / sprite.width
                sprite.scale_y = self._tile_height / sprite.height
                renderer.draw_sprite(sprite)

    def _clamp_col(self, value: int) -> int:
        return max(0, min(value, self._width))

    def _clamp_row(self, value: int) -> int:
        return max(0, min(value, self._height))

    def __repr__(self) -> str:
        return (
            f"TileMap({self._width}x{self._height}, "
            f"tile_size=({self._tile_width}, {self._tile_height}))"
        )


__all__ = ["TileMap"]
