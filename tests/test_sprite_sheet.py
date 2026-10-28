"""Tests for SpriteSheet region selection."""

import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture

from pydex_ge import ConfigurationError, Image, Sprite, SpriteSheet
from pydex_ge.backend.null import NullBackend


class SpriteSheetTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        path = write_fixture(self._tmp.name, "sheet.bmp", bmp_bytes(64, 32))
        self.image = Image(path, backend=NullBackend())

    def tearDown(self) -> None:
        self._tmp.cleanup()
        self.image.destroy()


class TestSpriteSheet(SpriteSheetTestBase):
    def test_sprite_region(self):
        sheet = SpriteSheet(self.image)
        sprite = sheet.sprite(x=0, y=0, width=32, height=32)
        self.assertIsInstance(sprite, Sprite)
        self.assertEqual((sprite.width, sprite.height), (32, 32))

    def test_region_output(self):
        sheet = SpriteSheet(self.image)
        region = sheet.region(x=16, y=8, width=8, height=8)
        self.assertEqual((region.x, region.y, region.width, region.height), (16, 8, 8, 8))

    def test_sheet_requires_image(self):
        with self.assertRaises(ConfigurationError):
            SpriteSheet("sheet.bmp")

    def test_region_outside_sheet_rejected(self):
        sheet = SpriteSheet(self.image)
        with self.assertRaises(ConfigurationError):
            sheet.sprite(x=60, y=0, width=10, height=10)

    def test_cell_needs_cell_size(self):
        sheet = SpriteSheet(self.image)
        with self.assertRaises(ConfigurationError):
            sheet.cell(0, 0)

    def test_cell_grid(self):
        sheet = SpriteSheet(self.image, cell_width=32, cell_height=32)
        self.assertEqual(sheet.columns, 2)
        self.assertEqual(sheet.rows, 1)
        sprite = sheet.cell(1, 0)
        self.assertEqual((sprite.width, sprite.height), (32, 32))

    def test_cell_outside_grid_rejected(self):
        sheet = SpriteSheet(self.image, cell_width=32, cell_height=32)
        with self.assertRaises(ConfigurationError):
            sheet.cell(5, 0)


if __name__ == "__main__":
    unittest.main()