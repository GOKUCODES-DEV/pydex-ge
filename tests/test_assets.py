"""Tests for the Assets image cache."""

import os
import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture

from pydex_ge import Assets
from pydex_ge.backend.null import NullBackend
from pydex_ge.exceptions import BackendError, ConfigurationError


class TestAssets(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "icon.bmp", bmp_bytes(16, 16))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _assets(self) -> Assets:
        return Assets(backend=NullBackend())

    def test_image_cached_by_path(self):
        assets = self._assets()
        first = assets.image(self._path)
        second = assets.image(self._path)
        self.assertIs(first, second)
        self.assertEqual(len(assets), 1)

    def test_cache_key_is_absolute(self):
        assets = self._assets()
        absolute = os.path.abspath(self._path)
        self.assertIs(assets.image(self._path), assets.image(absolute))

    def test_missing_file_raises(self):
        assets = self._assets()
        with self.assertRaises(BackendError):
            assets.image(os.path.join(self._tmp.name, "missing.bmp"))

    def test_contains(self):
        assets = self._assets()
        self.assertFalse(assets.contains(self._path))
        assets.image(self._path)
        self.assertTrue(assets.contains(self._path))

    def test_clear_destroys_and_empties(self):
        assets = self._assets()
        image = assets.image(self._path)
        assets.clear()
        self.assertEqual(len(assets), 0)
        self.assertFalse(assets.contains(self._path))
        with self.assertRaises(RuntimeError):
            image.width
        # Cache can be repopulated after clearing.
        again = assets.image(self._path)
        self.assertEqual(again.width, 16)


class TestAssetsFonts(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = os.path.join(self._tmp.name, "font.ttf")
        with open(self._path, "wb") as handle:
            handle.write(b"\x00\x01\x00\x00 fake ttf bytes")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _assets(self) -> Assets:
        return Assets(backend=NullBackend())

    def test_font_cached_by_path_and_size(self):
        assets = self._assets()
        first = assets.font(self._path, size=32)
        second = assets.font(self._path, size=32)
        self.assertIs(first, second)
        self.assertEqual(len(assets), 1)

    def test_font_size_distinguishes_cache_entries(self):
        assets = self._assets()
        small = assets.font(self._path, size=16)
        large = assets.font(self._path, size=32)
        self.assertIsNot(small, large)
        self.assertEqual(len(assets), 2)

    def test_font_default_size(self):
        assets = self._assets()
        self.assertIs(assets.font(self._path), assets.font(self._path, size=24))

    def test_font_path_normalized_relative_absolute(self):
        assets = self._assets()
        try:
            relative = os.path.relpath(self._path)
        except ValueError:
            self.skipTest("cwd and tempdir are on different drives")
        self.assertIs(assets.font(relative, size=16), assets.font(self._path, size=16))

    def test_font_invalid_size_rejected(self):
        assets = self._assets()
        for bad in (0, -1, True, 1.5, "big"):
            with self.assertRaises(ConfigurationError):
                assets.font(self._path, size=bad)

    def test_font_missing_file_raises(self):
        assets = self._assets()
        with self.assertRaises(BackendError):
            assets.font(os.path.join(self._tmp.name, "missing.ttf"))


class TestAssetsSpriteSheets(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "sheet.bmp", bmp_bytes(32, 32))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _assets(self) -> Assets:
        return Assets(backend=NullBackend())

    def test_sprite_sheet_cached(self):
        assets = self._assets()
        first = assets.sprite_sheet(self._path, 16, 16)
        second = assets.sprite_sheet(self._path, 16, 16)
        self.assertIs(first, second)
        self.assertEqual(len(assets), 2)

    def test_sheet_shares_cached_image(self):
        assets = self._assets()
        image = assets.image(self._path)
        sheet = assets.sprite_sheet(self._path, 16, 16)
        self.assertIs(sheet.image, image)

    def test_cell_size_distinguishes_sheets(self):
        assets = self._assets()
        a = assets.sprite_sheet(self._path, 16, 16)
        b = assets.sprite_sheet(self._path, 32, 32)
        self.assertIsNot(a, b)
        self.assertIs(a.image, b.image)

    def test_cell_sizes_optional(self):
        assets = self._assets()
        sheet = assets.sprite_sheet(self._path)
        self.assertIsNone(sheet.cell_width)
        self.assertIsNone(sheet.cell_height)

    def test_invalid_cell_sizes_rejected(self):
        assets = self._assets()
        for bad in (0, -1, True, "big", 1.5):
            with self.assertRaises(ConfigurationError):
                assets.sprite_sheet(self._path, bad, bad)

    def test_sheet_missing_file_raises(self):
        assets = self._assets()
        with self.assertRaises(BackendError):
            assets.sprite_sheet(os.path.join(self._tmp.name, "missing.bmp"), 16, 16)


class TestAssetsCleanup(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._image_path = write_fixture(self._tmp.name, "icon.bmp", bmp_bytes(16, 16))
        self._font_path = os.path.join(self._tmp.name, "font.ttf")
        with open(self._font_path, "wb") as handle:
            handle.write(b"\x00\x01\x00\x00 fake ttf bytes")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _assets(self) -> Assets:
        return Assets(backend=NullBackend())

    def test_remove_image_destroys_and_empties(self):
        assets = self._assets()
        image = assets.image(self._image_path)
        removed = assets.remove(self._image_path)
        self.assertEqual(removed, 1)
        self.assertEqual(len(assets), 0)
        self.assertFalse(assets.contains(self._image_path))
        with self.assertRaises(RuntimeError):
            image.width

    def test_remove_fonts_destroys_each_size(self):
        assets = self._assets()
        small = assets.font(self._font_path, size=16)
        large = assets.font(self._font_path, size=32)
        removed = assets.remove(self._font_path)
        self.assertEqual(removed, 2)
        self.assertEqual(len(assets), 0)
        with self.assertRaises(RuntimeError):
            small.measure("x")
        with self.assertRaises(RuntimeError):
            large.measure("x")

    def test_remove_sheet_drops_sheet_and_destroys_image(self):
        assets = self._assets()
        sheet = assets.sprite_sheet(self._image_path, 16, 16)
        removed = assets.remove(self._image_path)
        self.assertEqual(removed, 2)
        self.assertEqual(len(assets), 0)
        self.assertFalse(assets.contains(self._image_path))
        with self.assertRaises(RuntimeError):
            sheet.image.width

    def test_remove_unknown_path_returns_zero(self):
        assets = self._assets()
        self.assertEqual(assets.remove(os.path.join(self._tmp.name, "nope.bmp")), 0)

    def test_remove_is_idempotent(self):
        assets = self._assets()
        assets.image(self._image_path)
        self.assertEqual(assets.remove(self._image_path), 1)
        self.assertEqual(assets.remove(self._image_path), 0)

    def test_clear_destroys_all_asset_types(self):
        assets = self._assets()
        image = assets.image(self._image_path)
        font = assets.font(self._font_path, size=16)
        sheet = assets.sprite_sheet(self._image_path, 16, 16)
        assets.clear()
        self.assertEqual(len(assets), 0)
        with self.assertRaises(RuntimeError):
            image.width
        with self.assertRaises(RuntimeError):
            font.measure("x")
        with self.assertRaises(RuntimeError):
            sheet.image.width

    def test_clear_is_idempotent(self):
        assets = self._assets()
        assets.image(self._image_path)
        assets.clear()
        assets.clear()
        self.assertEqual(len(assets), 0)


class TestAssetsValidation(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _assets(self) -> Assets:
        return Assets(backend=NullBackend())

    def test_empty_paths_rejected(self):
        assets = self._assets()
        for bad in ("", "   ", None, 123, True):
            with self.assertRaises(ConfigurationError):
                assets.image(bad)
            with self.assertRaises(ConfigurationError):
                assets.font(bad)
            with self.assertRaises(ConfigurationError):
                assets.contains(bad)

    def test_missing_file_image_raises_backend_error(self):
        assets = self._assets()
        with self.assertRaises(BackendError):
            assets.image(os.path.join(self._tmp.name, "missing.bmp"))


if __name__ == "__main__":
    unittest.main()