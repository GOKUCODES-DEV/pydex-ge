"""Tests for the asset checks (ASSET001/002/003).

Covers missing literal asset paths, dynamic (unverifiable) paths, keyword
arguments, and duplicate-name detection.  There is no ``Sprite.from_file()``
in PYDEX; the path-taking sprite constructor is ``Sprite(path)``.  Likewise
``SpriteSheet`` takes an ``Image``, so a plain path is not its own asset.
"""

import os
import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture

import pydex_ge


class _ProjectDir(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, rel: str, text: str) -> str:
        path = os.path.join(self._dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path


class TestMissingAssets(_ProjectDir):
    def test_missing_asset_reported(self):
        self._write("main.py", 's = Sprite("player.png")\n')
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET001")
        self.assertEqual(results[0].category, "asset")
        self.assertEqual(results[0].severity, "error")
        self.assertIn("player.png", results[0].message)

    def test_existing_asset_ok(self):
        self._write("main.py", 's = Sprite("player.png")\n')
        write_fixture(self._dir, "player.png", bmp_bytes(8, 8))
        self.assertEqual(pydex_ge.check_assets(self._dir), [])

    def test_prefixed_pydex_sprite(self):
        self._write("main.py", 's = pydex_ge.Sprite("player.png")\n')
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET001")

    def test_assets_image_call(self):
        self._write("main.py", 'img = assets.image("icon.bmp")\n')
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET001")

    def test_audio_sound_call(self):
        self._write("main.py", 's = audio.load_sound("boom.wav")\n')
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET001")

    def test_keyword_source_sprite(self):
        self._write("main.py", 's = Sprite(source="player.png")\n')
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET001")

    def test_keyword_path_image(self):
        self._write("main.py", 'img = Image(path="icon.bmp")\n')
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET001")

    def test_keyword_path_assets_image(self):
        self._write("main.py", 'img = assets.image(path="icon.bmp")\n')
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET001")


class TestDynamicAssets(_ProjectDir):
    def test_dynamic_path_is_info(self):
        self._write("main.py", "s = Sprite(player_path)\n")
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET002")
        self.assertEqual(results[0].severity, "info")
        self.assertIn("player_path", results[0].message)

    def test_dynamic_keyword_path_is_info(self):
        self._write("main.py", "s = Sprite(source=player_path)\n")
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET002")
        self.assertIn("player_path", results[0].message)


class TestDuplicateAssets(_ProjectDir):
    def test_duplicate_basenames_warn(self):
        self._write("a/icon.png", "x")
        self._write("b/icon.png", "x")
        results = pydex_ge.check_assets(self._dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "ASSET003")
        self.assertEqual(results[0].severity, "warning")

    def test_unique_basenames_ok(self):
        write_fixture(self._dir, "a.png", bmp_bytes(4, 4))
        write_fixture(self._dir, "b.png", bmp_bytes(4, 4))
        self.assertEqual(pydex_ge.check_assets(self._dir), [])


class TestSingleFileAssets(_ProjectDir):
    def test_single_file_direct(self):
        path = self._write("main.py", 's = Sprite("nope.png")\n')
        report = pydex_ge.check_assets(path)
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0].code, "ASSET001")
        self.assertEqual(report[0].path, os.path.abspath(path))

    def test_single_file_with_local_asset(self):
        path = self._write("main.py", 's = Sprite("local.png")\n')
        write_fixture(self._dir, "local.png", bmp_bytes(4, 4))
        self.assertEqual(pydex_ge.check_assets(path), [])


class TestNonPathConstructors(_ProjectDir):
    def test_sprite_from_file_is_not_an_asset_call(self):
        # ``Sprite.from_file`` does not exist; the checker flags the wrong
        # attribute through PYDEX002, not an asset check.
        self._write("main.py", 's = Sprite.from_file("player.png")\n')
        self.assertEqual(pydex_ge.check_assets(self._dir), [])

    def test_sprite_sheet_path_is_not_direct_asset(self):
        # ``SpriteSheet`` wraps an ``Image``; the real asset call is the
        # inner ``Image(path)`` which the checker already catches.
        self._write("main.py", 'sheet = SpriteSheet("tiles.png")\n')
        self.assertEqual(pydex_ge.check_assets(self._dir), [])


if __name__ == "__main__":
    unittest.main()