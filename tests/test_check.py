"""Tests for pydex_ge.check: syntax checking, project scanning, and format_error.

These also verify the standardized ``Missing asset: ...`` messages and their
requester-context reporting.
"""

import os
import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture

import pydex_ge
from pydex_ge import ConfigurationError, MissingAssetError
from pydex_ge.backend.null import NullBackend


class TestCheckFile(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, name: str, text: str) -> str:
        path = os.path.join(self._dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_valid_file_returns_empty(self):
        path = self._write("good.py", "x = 1\nprint(x)\n")
        self.assertEqual(pydex_ge.check_file(path), [])

    def test_syntax_error_reports_line_and_column(self):
        path = self._write("bad.py", "def broken(:\n    pass\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.path, os.path.abspath(path))
        self.assertEqual(result.lineno, 1)
        self.assertEqual(result.column, 12)
        self.assertEqual(result.message, "invalid syntax")

    def test_error_on_second_line(self):
        path = self._write("bad2.py", "x = 1\ny = x +\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].lineno, 2)
        self.assertEqual(results[0].column, 8)

    def test_str_includes_location_and_message(self):
        path = self._write("bad3.py", "def broken(:\n    pass\n")
        rendered = str(pydex_ge.check_file(path)[0])
        self.assertTrue(rendered.startswith(os.path.abspath(path) + ":1:12: "))
        self.assertTrue(rendered.endswith("invalid syntax"))

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            pydex_ge.check_file(os.path.join(self._dir, "nope.py"))

    def test_non_string_path_rejected(self):
        for bad in ("", "   ", None, 123):
            with self.assertRaises(ConfigurationError):
                pydex_ge.check_file(bad)

    def test_encoding_cookie_supported(self):
        path = self._write("bad4.py", "# -*- coding: utf-8 -*-\ndef broken(:\n    pass\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].lineno, 2)


class TestCheckProject(unittest.TestCase):
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

    def test_scans_all_python_files(self):
        self._write("good.py", "x = 1\n")
        self._write("sub/bad.py", "def broken(:\n    pass\n")
        self._write("sub/deep/also_bad.py", "y = (\n")
        results = pydex_ge.check_project(self._dir)
        paths = sorted(r.path for r in results)
        self.assertEqual(len(paths), 2)
        self.assertTrue(any(p.endswith(os.path.join("sub", "bad.py")) for p in paths))
        self.assertTrue(any(p.endswith(os.path.join("sub", "deep", "also_bad.py")) for p in paths))

    def test_ignores_non_python_files(self):
        self._write("notes.txt", "def broken(:\n")
        self._write("data.png", "not python")
        self.assertEqual(pydex_ge.check_project(self._dir), [])

    def test_skips_hidden_and_vendor_directories(self):
        self._write(".hidden/bad.py", "def broken(:\n    pass\n")
        self._write("__pycache__/bad.py", "def broken(:\n    pass\n")
        self._write("node_modules/bad.py", "def broken(:\n    pass\n")
        self.assertEqual(pydex_ge.check_project(self._dir), [])

    def test_default_root_is_cwd(self):
        previous = os.getcwd()
        os.chdir(self._dir)
        try:
            self._write("bad.py", "def broken(:\n    pass\n")
            results = pydex_ge.check_project()
            self.assertEqual(len(results), 1)
        finally:
            os.chdir(previous)

    def test_missing_root_raises(self):
        with self.assertRaises(NotADirectoryError):
            pydex_ge.check_project(os.path.join(self._dir, "missing"))


class TestFormatError(unittest.TestCase):
    def test_formats_syntax_error_with_location(self):
        source = "def broken(:\n    pass\n"
        try:
            compile(source, "game.py", "exec")
        except SyntaxError as exc:
            rendered = pydex_ge.format_error(exc)
        self.assertEqual(rendered, "game.py:1:12: SyntaxError: invalid syntax")

    def test_prefers_requester_location_for_missing_asset(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        assets = pydex_ge.Assets(backend=NullBackend())
        try:
            assets.image(os.path.join(tmp.name, "missing.png"))
        except MissingAssetError as exc:
            rendered = pydex_ge.format_error(exc)
        self.assertIn("MissingAssetError: Missing asset: missing.png", rendered)
        self.assertIn("test_check.py", rendered)

    def test_config_error_location_reported(self):
        try:
            pydex_ge.Game("x", 640, 480, fps=0, backend=NullBackend())
        except ConfigurationError as exc:
            rendered = pydex_ge.format_error(exc)
        self.assertIn("ConfigurationError: fps must be a positive number", rendered)
        self.assertIn("test_check.py", rendered)

    def test_unknown_location_falls_back(self):
        exc = RuntimeError("boom")
        rendered = pydex_ge.format_error(exc)
        self.assertTrue(rendered.endswith("RuntimeError: boom"))


class TestMissingAssetError(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = self._tmp.name
        self._assets = pydex_ge.Assets(backend=NullBackend())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _missing(self) -> str:
        return os.path.join(self._dir, "player.png")

    def test_message_says_missing_asset(self):
        try:
            self._assets.image(self._missing())
        except MissingAssetError as exc:
            self.assertIn("Missing asset: player.png", str(exc))
            self.assertIn("looked for", str(exc))
            self.assertEqual(exc.path, os.path.normcase(os.path.abspath(self._missing())))

    def test_is_a_backend_and_pydex_error(self):
        try:
            self._assets.image(self._missing())
        except MissingAssetError as exc:
            self.assertIsInstance(exc, pydex_ge.BackendError)
            self.assertIsInstance(exc, pydex_ge.PydexError)

    def test_requested_by_is_set(self):
        try:
            self._assets.image(self._missing())
        except MissingAssetError as exc:
            self.assertIsNotNone(exc.requested_by)
            self.assertIn("test_check.py", exc.requested_by)

    def test_font_missing_asset_message(self):
        try:
            self._assets.font(os.path.join(self._dir, "missing.ttf"))
        except MissingAssetError as exc:
            self.assertIn("Missing asset: missing.ttf", str(exc))

    def test_image_object_missing_asset(self):
        from pydex_ge import Image

        try:
            Image(self._missing(), backend=NullBackend())
        except MissingAssetError as exc:
            self.assertIn("Missing asset: player.png", str(exc))

    def test_sprite_missing_asset(self):
        from pydex_ge import Sprite

        try:
            Sprite(self._missing(), backend=NullBackend())
        except MissingAssetError as exc:
            self.assertIn("Missing asset: player.png", str(exc))

    def test_audio_sound_missing_asset(self):
        from pydex_ge import Audio

        audio = Audio(backend=NullBackend())
        self.addCleanup(audio.close)
        try:
            audio.load_sound(os.path.join(self._dir, "missing.wav"))
        except MissingAssetError as exc:
            self.assertIn("Missing asset: missing.wav", str(exc))

    def test_audio_music_missing_asset(self):
        from pydex_ge import Audio

        audio = Audio(backend=NullBackend())
        self.addCleanup(audio.close)
        try:
            audio.load_music(os.path.join(self._dir, "missing.ogg"))
        except MissingAssetError as exc:
            self.assertIn("Missing asset: missing.ogg", str(exc))

    def test_splash_missing_asset(self):
        splash = pydex_ge.SplashScreen(file_checking=True, loadables=[("image", self._missing())])
        splash.width, splash.height = 800, 600
        try:
            splash._check_files()
        except MissingAssetError as exc:
            self.assertIn("Missing asset: player.png", str(exc))
            self.assertIn("test_check.py", exc.requested_by)

    def test_valid_asset_still_loads(self):
        path = write_fixture(self._dir, "icon.bmp", bmp_bytes(16, 16))
        image = self._assets.image(path)
        self.assertEqual((image.width, image.height), (16, 16))


if __name__ == "__main__":
    unittest.main()
