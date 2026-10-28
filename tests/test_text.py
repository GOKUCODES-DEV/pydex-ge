"""Tests for the Text class."""

import os
import tempfile
import unittest

from _stub_backend import StubBackend

import pydex_ge
from pydex_ge.exceptions import ConfigurationError


def _make_font_file(directory: str, name: str = "font.ttf") -> str:
    path = os.path.join(directory, name)
    with open(path, "wb") as handle:
        handle.write(b"\x00\x01\x00\x00 fake ttf bytes")
    return path


class TextTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.font_path = _make_font_file(self.tmp.name)
        self.backend = StubBackend()
        self.font = pydex_ge.Font(self.font_path, size=24, backend=self.backend)


class TestTextConstruction(TextTestBase):
    def test_create_with_font(self):
        text = pydex_ge.Text("Hello", font=self.font)
        self.assertIs(text.font, self.font)
        text.destroy()

    def test_create_with_font_path(self):
        text = pydex_ge.Text("Hi", font=self.font_path, backend=self.backend)
        self.assertTrue(text.font.path)
        text.destroy()

    def test_create_with_none_uses_system_font(self):
        from unittest import mock

        import pydex_ge.graphics.font as font_module

        with mock.patch.object(font_module, "_find_system_font", return_value=self.font_path):
            text = pydex_ge.Text("Hi", backend=self.backend)
            self.assertTrue(text.font.path)
            text.destroy()

    def test_text_must_be_string(self):
        with self.assertRaises(ConfigurationError):
            pydex_ge.Text(123, font=self.font)


class TestTextState(TextTestBase):
    def test_text_updates(self):
        text = pydex_ge.Text("Before", font=self.font)
        text.text = "After"
        self.assertEqual(text.text, "After")
        text.destroy()

    def test_position_and_color(self):
        text = pydex_ge.Text("Hi", font=self.font, position=(10, 20), color=(0, 255, 0))
        self.assertEqual(text.position, (10, 20))
        self.assertEqual(text.color, (0, 255, 0, 255))
        text.destroy()

    def test_visible_default_true(self):
        text = pydex_ge.Text("Hi", font=self.font)
        self.assertTrue(text.visible)
        text.destroy()

    def test_font_size_of_shared_font(self):
        text = pydex_ge.Text("Hi", font=self.font)
        self.assertEqual(text.font_size, 24)
        with self.assertRaises(ConfigurationError):
            text.font_size = 30
        text.destroy()

    def test_width_height(self):
        text = pydex_ge.Text("Hello", font=self.font)
        width, height = self.font.measure("Hello")
        self.assertEqual(text.width, width)
        self.assertEqual(text.height, height)
        text.destroy()

    def test_destroy_owned_font_only(self):
        text = pydex_ge.Text("Hi", font=self.font_path, backend=self.backend)
        owned = text.font
        text.destroy()
        self.assertTrue(owned._destroyed)
        # shared font unaffected
        shared = pydex_ge.Text("Hi", font=self.font)
        shared.destroy()
        self.assertFalse(self.font._destroyed)


if __name__ == "__main__":
    unittest.main()
