"""Tests for the Part 12 TileMap: grid, sprite sheet, solid tiles, collision,
and camera-culled rendering."""

import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import (
    Body,
    Camera,
    ConfigurationError,
    Image,
    Rect,
    Renderer,
    SpriteSheet,
    TileMap,
    Vector2,
)


class TileMapTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "sheet.bmp", bmp_bytes(64, 32))
        self.backend = StubBackend(image_sizes={self._path: (64, 32)})
        self.renderer = Renderer(StubRenderer())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _image(self) -> Image:
        return Image(self._path, backend=self.backend)

    def _sheet(self) -> SpriteSheet:
        return SpriteSheet(self._image(), 32, 32)


class TestTileMapConstruction(unittest.TestCase):
    def test_dimensions(self):
        tiles = TileMap(10, 5, tile_size=(32, 32))
        self.assertEqual(tiles.width, 10)
        self.assertEqual(tiles.height, 5)
        self.assertEqual(tiles.cols, 10)
        self.assertEqual(tiles.rows, 5)
        self.assertEqual(tiles.tile_size, (32, 32))
        self.assertEqual(tiles.pixel_width, 320)
        self.assertEqual(tiles.pixel_height, 160)

    def test_empty_by_default(self):
        tiles = TileMap(4, 3)
        self.assertEqual(tiles.get_tile(0, 0), 0)
        self.assertIsNone(tiles.sprite_sheet)

    def test_tiles_from_2d_list(self):
        tiles = TileMap(2, 2, tiles=[[1, 2], [0, 1]])
        self.assertEqual(tiles.get_tile(0, 0), 1)
        self.assertEqual(tiles.get_tile(1, 0), 2)
        self.assertEqual(tiles.get_tile(0, 1), 0)
        self.assertEqual(tiles.get_tile(1, 1), 1)

    def test_invalid_dimensions(self):
        with self.assertRaises(ConfigurationError):
            TileMap(0, 5)
        with self.assertRaises(ConfigurationError):
            TileMap(5, -1)
        with self.assertRaises(ConfigurationError):
            TileMap(True, 5)

    def test_invalid_tile_size(self):
        with self.assertRaises(ConfigurationError):
            TileMap(4, 4, tile_size=16)
        with self.assertRaises(ConfigurationError):
            TileMap(4, 4, tile_size=(0, 32))

    def test_tiles_shape_mismatch(self):
        with self.assertRaises(ConfigurationError):
            TileMap(2, 2, tiles=[[1, 2, 3], [1, 2]])
        with self.assertRaises(ConfigurationError):
            TileMap(2, 2, tiles=[[1, 2]])
        with self.assertRaises(ConfigurationError):
            TileMap(2, 2, tiles="xy")

    def test_invalid_tile_id(self):
        tiles = TileMap(2, 2)
        with self.assertRaises(ConfigurationError):
            tiles.set_tile(0, 0, -1)


class TestTileMapGrid(TileMapTestBase):
    def test_set_and_get(self):
        tiles = TileMap(4, 3)
        tiles.set_tile(2, 1, 5)
        self.assertEqual(tiles.get_tile(2, 1), 5)
        self.assertEqual(tiles.get_tile(0, 0), 0)

    def test_out_of_range(self):
        tiles = TileMap(4, 3)
        with self.assertRaises(ConfigurationError):
            tiles.get_tile(4, 0)
        with self.assertRaises(ConfigurationError):
            tiles.set_tile(0, 3, 1)
        with self.assertRaises(ConfigurationError):
            tiles.set_tile(-1, 0, 1)

    def test_clear(self):
        tiles = TileMap(4, 3)
        tiles.set_tile(1, 1, 2)
        tiles.clear()
        self.assertEqual(tiles.get_tile(1, 1), 0)

    def test_tile_rect(self):
        tiles = TileMap(4, 3, tile_size=(32, 16))
        rect = tiles.tile_rect(2, 1)
        self.assertEqual(rect, Rect(64, 16, 32, 16))

    def test_tile_at(self):
        tiles = TileMap(4, 3, tile_size=(32, 32))
        self.assertEqual(tiles.tile_at(0, 0), (0, 0))
        self.assertEqual(tiles.tile_at(31, 63), (0, 1))
        self.assertEqual(tiles.tile_at(70, 10), (2, 0))
        self.assertIsNone(tiles.tile_at(-1, 0))
        self.assertIsNone(tiles.tile_at(0, 300))
        self.assertIsNone(tiles.tile_at(400, 0))
        with self.assertRaises(ConfigurationError):
            tiles.tile_at("x", 0)


class TestTileMapSolid(TileMapTestBase):
    def test_set_solid_and_is_solid(self):
        tiles = TileMap(4, 3)
        self.assertFalse(tiles.is_solid(1))
        tiles.set_solid(1)
        self.assertTrue(tiles.is_solid(1))
        tiles.set_solid(1, False)
        self.assertFalse(tiles.is_solid(1))

    def test_solid_requires_bool(self):
        tiles = TileMap(4, 3)
        with self.assertRaises(ConfigurationError):
            tiles.set_solid(1, solid="yes")

    def test_solid_rects_merges_runs(self):
        tiles = TileMap(5, 2, tile_size=(32, 32))
        tiles.set_solid(1)
        tiles.set_tile(1, 0, 1)
        tiles.set_tile(2, 0, 1)
        tiles.set_tile(3, 0, 1)
        tiles.set_tile(1, 1, 1)
        rects = tiles.solid_rects()
        self.assertEqual(
            rects,
            [
                Rect(32, 0, 96, 32),   # merged horizontal run on row 0
                Rect(32, 32, 32, 32),  # row 1
            ],
        )

    def test_collide_body_pushes_out(self):
        tiles = TileMap(3, 3, tile_size=(32, 32))
        tiles.set_solid(1)
        tiles.set_tile(1, 1, 1)
        body = Body(position=(40, 40), size=(16, 16), velocity=(0, 100))
        self.assertTrue(tiles.collide_body(body))
        # Falling straight down into a tile: the body is pushed out on top
        # (velocity-aware resolution), not ejected through a side.
        self.assertEqual(body.position, Vector2(40, 16))
        self.assertEqual(body.velocity, Vector2(0, 0))

    def test_collide_body_side_push_respects_velocity(self):
        tiles = TileMap(3, 3, tile_size=(32, 32))
        tiles.set_solid(1)
        tiles.set_tile(1, 1, 1)
        body = Body(position=(40, 40), size=(16, 16), velocity=(100, 0))
        self.assertTrue(tiles.collide_body(body))
        # Moving right into a tile: pushed back out to the left, x stopped.
        self.assertEqual(body.position.x, 16.0)
        self.assertEqual(body.velocity, Vector2(0, 0))

    def test_collide_body_no_hit(self):
        tiles = TileMap(3, 3, tile_size=(32, 32))
        tiles.set_solid(1)
        tiles.set_tile(1, 1, 1)
        body = Body(position=(0, 0), size=(10, 10))
        self.assertFalse(tiles.collide_body(body))


class TestTileMapSpriteSheet(TileMapTestBase):
    def test_sprite_sheet_validation(self):
        tiles = TileMap(4, 3)
        with self.assertRaises(ConfigurationError):
            tiles.sprite_sheet = "not a sheet"
        tiles.sprite_sheet = None
        self.assertIsNone(tiles.sprite_sheet)

    def test_render_requires_sheet(self):
        tiles = TileMap(4, 3)
        tiles.set_tile(0, 0, 1)
        tiles.render(self.renderer)  # silently skips without a sheet
        self.assertEqual(len(self.renderer._renderer.texture_draws), 0)


class TestTileMapRender(TileMapTestBase):
    def test_render_draws_nonempty_tiles(self):
        tiles = TileMap(4, 3, tile_size=(32, 32), sprite_sheet=self._sheet())
        tiles.set_tile(0, 0, 1)
        tiles.set_tile(2, 1, 2)
        tiles.render(self.renderer)
        draws = self.renderer._renderer.texture_draws
        self.assertEqual(len(draws), 2)
        _, src, dst, _ = draws[0]
        self.assertEqual(dst, (0, 0, 32, 32))
        _, src, dst, _ = draws[1]
        self.assertEqual(dst, (64, 32, 32, 32))

    def test_render_skips_empty_tiles(self):
        tiles = TileMap(4, 3, tile_size=(32, 32), sprite_sheet=self._sheet())
        tiles.set_tile(1, 1, 1)
        tiles.render(self.renderer)
        self.assertEqual(len(self.renderer._renderer.texture_draws), 1)

    def test_render_with_camera_culls(self):
        tiles = TileMap(10, 1, tile_size=(32, 32), sprite_sheet=self._sheet())
        tiles.set_tile(0, 0, 1)
        tiles.set_tile(9, 0, 1)
        camera = Camera(position=(0, 0))
        self.renderer.begin_camera(camera)
        try:
            tiles.render(self.renderer)
        finally:
            self.renderer.end_camera()
        self.assertEqual(len(self.renderer._renderer.texture_draws), 2)

    def test_render_with_far_camera_draws_nothing(self):
        tiles = TileMap(10, 1, tile_size=(32, 32), sprite_sheet=self._sheet())
        tiles.set_tile(0, 0, 1)
        tiles.set_tile(9, 0, 1)
        camera = Camera(position=(2000, 0))
        self.renderer.begin_camera(camera)
        try:
            tiles.render(self.renderer)
        finally:
            self.renderer.end_camera()
        self.assertEqual(len(self.renderer._renderer.texture_draws), 0)

    def test_render_uses_active_camera(self):
        tiles = TileMap(10, 1, tile_size=(32, 32), sprite_sheet=self._sheet())
        tiles.set_tile(0, 0, 1)
        camera = Camera(position=(2000, 0))
        self.renderer.begin_camera(camera)
        try:
            tiles.render(self.renderer)
        finally:
            self.renderer.end_camera()
        self.assertEqual(len(self.renderer._renderer.texture_draws), 0)


if __name__ == "__main__":
    unittest.main()
