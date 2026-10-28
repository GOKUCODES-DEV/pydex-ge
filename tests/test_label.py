"""Tests for the Label and Text classes, using a stub backend."""

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


class LabelTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.font_path = _make_font_file(self.tmp.name)
        self.backend = StubBackend()
        self.font = pydex_ge.Font(self.font_path, size=24, backend=self.backend)


class TestLabelConstruction(LabelTestBase):
    def test_create_with_position_only(self):
        label = pydex_ge.Label("Hello PYDEX", position=(100, 100), backend=self.backend)
        self.assertEqual(label.text, "Hello PYDEX")
        self.assertEqual(label.position, (100, 100))
        self.assertEqual(label.color, (255, 255, 255, 255))
        self.assertTrue(label.visible)
        label.destroy()

    def test_create_with_shared_font(self):
        label = pydex_ge.Label("My Game", font=self.font, position=(10, 20))
        self.assertIs(label.font, self.font)
        label.destroy()

    def test_create_with_font_path(self):
        label = pydex_ge.Label("Hi", font=self.font_path, position=(0, 0), backend=self.backend)
        self.assertNotEqual(label.font.path, "")
        label.destroy()

    def test_invalid_text_rejected(self):
        with self.assertRaises(ConfigurationError):
            pydex_ge.Label(123, backend=self.backend)

    def test_invalid_position_rejected(self):
        for bad in ((1.5, 2), ("x", 0), (1, "y"), True, 5):
            with self.assertRaises(ConfigurationError):
                pydex_ge.Label("Hi", position=bad, backend=self.backend)

    def test_invalid_color_rejected(self):
        for bad in ((1, 2), (1, 2, 3, 4, 5), (256, 0, 0), "red", (0, 0, -1)):
            with self.assertRaises(ConfigurationError):
                pydex_ge.Label("Hi", color=bad, backend=self.backend)

    def test_invalid_font_size_rejected(self):
        for bad in (0, -4, True, 1.5, "big"):
            with self.assertRaises(ConfigurationError):
                pydex_ge.Label("Hi", font_size=bad, backend=self.backend)


class TestLabelState(LabelTestBase):
    def test_text_updates(self):
        label = pydex_ge.Label("Press E", font=self.font)
        label.text = "E was pressed!"
        self.assertEqual(label.text, "E was pressed!")
        label.destroy()

    def test_text_must_be_string(self):
        label = pydex_ge.Label("Press E", font=self.font)
        with self.assertRaises(ConfigurationError):
            label.text = 123
        label.destroy()

    def test_position_settable(self):
        label = pydex_ge.Label("Hi", font=self.font, position=(1, 2))
        label.position = (30, 40)
        self.assertEqual(label.position, (30, 40))
        label.x = 5
        label.y = 7
        self.assertEqual((label.x, label.y), (5, 7))
        label.destroy()

    def test_color_settable(self):
        label = pydex_ge.Label("Hi", font=self.font)
        label.color = (255, 0, 0)
        self.assertEqual(label.color, (255, 0, 0, 255))
        label.destroy()

    def test_visible_flag(self):
        label = pydex_ge.Label("Hi", font=self.font)
        label.visible = False
        self.assertFalse(label.visible)
        label.visible = True
        self.assertTrue(label.visible)
        label.destroy()

    def test_measured_size(self):
        label = pydex_ge.Label("Hello", font=self.font)
        self.assertGreater(label.width, 0)
        self.assertEqual(label.height, 24)
        label.destroy()


class TestLabelDrawing(LabelTestBase):
    def _core_renderer(self):
        from pydex_ge.core.renderer import Renderer

        renderer = self.backend.create_renderer(self.backend.create_window("t", 100, 100))
        return Renderer(renderer), renderer

    def test_draw_records_texture(self):
        label = pydex_ge.Label("Hello", font=self.font, position=(5, 7))
        core, renderer = self._core_renderer()
        core.draw_label(label)
        self.assertEqual(len(renderer.texture_draws), 1)
        texture, src, dst, alpha = renderer.texture_draws[0]
        self.assertIsNone(src)
        self.assertEqual(dst[0], 5)
        self.assertEqual(dst[1], 7)
        self.assertEqual(alpha, 255)
        core.destroy()
        label.destroy()

    def test_invisible_label_draws_nothing(self):
        label = pydex_ge.Label("Hello", font=self.font)
        label.visible = False
        core, renderer = self._core_renderer()
        core.draw_label(label)
        self.assertEqual(len(renderer.texture_draws), 0)
        core.destroy()
        label.destroy()

    def test_text_draw_and_label_draw_are_equivalent(self):
        label = pydex_ge.Label("Hello", font=self.font)
        text = pydex_ge.Text("Hello", font=self.font)
        core, renderer = self._core_renderer()
        core.draw_label(label)
        core.draw_text(text)
        self.assertEqual(len(renderer.texture_draws), 2)
        core.destroy()
        label.destroy()
        text.destroy()


class TestSharedFontOwnership(LabelTestBase):
    def test_destroying_label_does_not_destroy_shared_font(self):
        label = pydex_ge.Label("Hi", font=self.font)
        label.destroy()
        # Shared font stays usable.
        self.assertEqual(self.font.size, 24)
        self.assertGreater(self.font.measure("still works")[0], 0)

    def test_shared_font_survives_ownerless_labels(self):
        a = pydex_ge.Label("A", font=self.font)
        b = pydex_ge.Label("B", font=self.font)
        a.destroy()
        b.destroy()
        self.assertEqual(self.font.size, 24)

    def test_font_size_setter_rejects_shared_font(self):
        label = pydex_ge.Label("Hi", font=self.font)
        with self.assertRaises(ConfigurationError):
            label.font_size = 40
        label.destroy()

    def test_owned_font_size_setter_rebuilds(self):
        label = pydex_ge.Label("Hi", font=self.font_path, font_size=20, backend=self.backend)
        original = label.font
        label.font_size = 40
        self.assertEqual(label.font_size, 40)
        self.assertIsNot(label.font, original)
        label.destroy()


if __name__ == "__main__":
    unittest.main()
