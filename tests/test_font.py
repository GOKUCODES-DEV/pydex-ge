"""Tests for the Font class, using a stub backend and temp font files."""

import os
import tempfile
import unittest
from unittest import mock

from _stub_backend import StubBackend

import pydex_ge
from pydex_ge.exceptions import BackendError, ConfigurationError


def _make_font_file(directory: str, name: str = "font.ttf") -> str:
    path = os.path.join(directory, name)
    with open(path, "wb") as handle:
        handle.write(b"\x00\x01\x00\x00 fake ttf bytes")
    return path


class TestFontLoading(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.font_path = _make_font_file(self.tmp.name)
        self.backend = StubBackend()

    def test_load_with_explicit_path(self):
        font = pydex_ge.Font(self.font_path, size=32, backend=self.backend)
        self.assertEqual(font.size, 32)
        self.assertTrue(font.path)
        font.destroy()

    def test_otf_extension_supported(self):
        otf_path = _make_font_file(self.tmp.name, "font.otf")
        font = pydex_ge.Font(otf_path, size=20, backend=self.backend)
        self.assertEqual(font.size, 20)
        font.destroy()

    def test_relative_path_resolves_against_cwd(self):
        original = os.getcwd()
        backend = StubBackend()
        try:
            os.chdir(self.tmp.name)
            font = pydex_ge.Font("font.ttf", size=16, backend=backend)
            self.assertEqual(font.path, os.path.join(self.tmp.name, "font.ttf"))
            font.destroy()
        finally:
            os.chdir(original)

    def test_absolute_path(self):
        font = pydex_ge.Font(self.font_path, size=16, backend=self.backend)
        self.assertEqual(font.path, os.path.abspath(self.font_path))
        font.destroy()

    def test_missing_file_raises_backend_error(self):
        backend = StubBackend()
        with self.assertRaises(BackendError):
            pydex_ge.Font(os.path.join(self.tmp.name, "nope.ttf"), size=16, backend=backend)

    def test_empty_path_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            pydex_ge.Font("   ", size=16, backend=StubBackend())

    def test_invalid_size_rejected(self):
        backend = StubBackend()
        for bad in (0, -5, True, "big", 1.5):
            with self.assertRaises(ConfigurationError):
                pydex_ge.Font(self.font_path, size=bad, backend=backend)

    def test_measure(self):
        font = pydex_ge.Font(self.font_path, size=24, backend=StubBackend())
        width, height = font.measure("Hello")
        self.assertGreater(width, 0)
        self.assertEqual(height, 24)
        font.destroy()

    def test_measure_requires_string(self):
        font = pydex_ge.Font(self.font_path, size=24, backend=StubBackend())
        with self.assertRaises(ConfigurationError):
            font.measure(123)
        font.destroy()

    def test_destroy_is_idempotent(self):
        font = pydex_ge.Font(self.font_path, size=24, backend=StubBackend())
        font.destroy()
        font.destroy()

    def test_font_unusable_after_destroy(self):
        font = pydex_ge.Font(self.font_path, size=24, backend=StubBackend())
        font.destroy()
        with self.assertRaises(RuntimeError):
            font.measure("Hello")


class TestFontCaching(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.font_path = _make_font_file(self.tmp.name)
        self.backend = StubBackend()

    def test_same_path_and_size_reuses_backend_font(self):
        backend = StubBackend()
        font_a = pydex_ge.Font(self.font_path, size=24, backend=backend)
        font_b = pydex_ge.Font(self.font_path, size=24, backend=backend)
        self.assertIs(font_a._backend_font, font_b._backend_font)
        font_a.destroy()
        font_b.destroy()

    def test_different_size_reloads(self):
        backend = StubBackend()
        font_a = pydex_ge.Font(self.font_path, size=24, backend=backend)
        font_b = pydex_ge.Font(self.font_path, size=48, backend=backend)
        self.assertIsNot(font_a._backend_font, font_b._backend_font)
        font_a.destroy()
        font_b.destroy()

    def test_destroy_evicts_cache(self):
        backend = StubBackend()
        font_a = pydex_ge.Font(self.font_path, size=24, backend=backend)
        cached = font_a._backend_font
        font_a.destroy()
        font_b = pydex_ge.Font(self.font_path, size=24, backend=backend)
        self.assertIsNot(font_b._backend_font, cached)
        font_b.destroy()


class TestSystemFontFallback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.font_path = _make_font_file(self.tmp.name)
        self.backend = StubBackend()
    def test_system_font_used_when_no_path(self):
        backend = StubBackend()
        with mock.patch(
            "pydex_ge.graphics.font._find_system_font", return_value=self.font_path
        ) as finder:
            font = pydex_ge.Font(size=24, backend=backend)
            self.assertTrue(font.path)
            font.destroy()
            finder.assert_called_once()

    def test_error_when_no_system_font(self):
        backend = StubBackend()
        with mock.patch("pydex_ge.graphics.font._find_system_font", return_value=None):
            with self.assertRaises(ConfigurationError):
                pydex_ge.Font(size=24, backend=backend)

    def test_custom_font_bypasses_system_search(self):
        backend = StubBackend()
        with mock.patch("pydex_ge.graphics.font._find_system_font") as finder:
            font = pydex_ge.Font(self.font_path, size=24, backend=backend)
            finder.assert_not_called()
            font.destroy()


if __name__ == "__main__":
    unittest.main()
