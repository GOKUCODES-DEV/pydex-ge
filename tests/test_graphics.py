"""Tests for colors and the 2D drawing commands (using a stub renderer)."""

import unittest

from _stub_backend import StubRenderer

from pydex_ge import ConfigurationError, Game
from pydex_ge.backend.null import NullBackend
from pydex_ge.core.renderer import Renderer
from pydex_ge.graphics.color import normalize_rgb, normalize_rgba
from pydex_ge.graphics.drawing import DrawCommands


def _draw() -> DrawCommands:
    return Renderer(StubRenderer()).draw


class TestColors(unittest.TestCase):
    def test_valid_rgb(self):
        self.assertEqual(normalize_rgb((255, 100, 50)), (255, 100, 50))

    def test_rgb_list_input(self):
        self.assertEqual(normalize_rgb([10, 20, 30]), (10, 20, 30))

    def test_rgba_keeps_alpha(self):
        self.assertEqual(normalize_rgba((1, 2, 3, 200)), (1, 2, 3, 200))

    def test_rgba_from_rgb_defaults_alpha_to_255(self):
        self.assertEqual(normalize_rgba((1, 2, 3)), (1, 2, 3, 255))

    def test_wrong_lengths_rejected(self):
        for length in ((), (0,), (0, 0), (0, 0, 0, 0), (0, 0, 0, 0, 0)):
            with self.assertRaises(ConfigurationError):
                normalize_rgb(length)
        for length in ((), (0,), (0, 0), (0, 0, 0, 0, 0)):
            with self.assertRaises(ConfigurationError):
                normalize_rgba(length)

    def test_wrong_types_rejected(self):
        for bad in ("red", 5, None, (255, "0", 0), (255, 0.5, 0), (255, 0, True)):
            with self.assertRaises(ConfigurationError):
                normalize_rgb(bad)

    def test_out_of_range_rejected(self):
        for bad in ((0, 0, 256), (0, 0, -1), (300, 0, 0), (0, 0, 0, 999)):
            with self.assertRaises(ConfigurationError):
                normalize_rgba(bad)


class TestDrawCommands(unittest.TestCase):
    def test_pixel_forwards_coordinates_and_color(self):
        backend = StubRenderer()
        Renderer(backend).draw.pixel(3, 4)
        self.assertEqual(backend.pixels, [(3, 4, (255, 255, 255, 255))])

    def test_pixel_preserves_rgba(self):
        backend = StubRenderer()
        Renderer(backend).draw.pixel(1, 2, color=(0, 128, 255, 90))
        self.assertEqual(backend.pixels[0][2], (0, 128, 255, 90))

    def test_pixel_rejects_bad_coordinates(self):
        draw = _draw()
        for bad in (1.5, True, "1"):
            with self.assertRaises(ConfigurationError):
                draw.pixel(bad, 0)

    def test_line_forwards_all_arguments(self):
        backend = StubRenderer()
        Renderer(backend).draw.line(1, 2, 3, 4, color=(10, 20, 30))
        self.assertEqual(backend.lines, [(1, 2, 3, 4, (10, 20, 30, 255))])

    def test_rect_filled_by_default(self):
        backend = StubRenderer()
        Renderer(backend).draw.rect(5, 6, 200, 100, color=(255, 0, 0))
        self.assertEqual(backend.rects, [(5, 6, 200, 100, (255, 0, 0, 255), True)])

    def test_rect_outline_mode(self):
        backend = StubRenderer()
        Renderer(backend).draw.rect(5, 6, 200, 100, color=(0, 255, 0), filled=False)
        self.assertEqual(backend.rects[0][5], False)

    def test_rect_rejects_invalid_dimensions(self):
        draw = _draw()
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ConfigurationError):
                draw.rect(0, 0, bad, 10)
            with self.assertRaises(ConfigurationError):
                draw.rect(0, 0, 10, bad)

    def test_circle_forwards_arguments(self):
        backend = StubRenderer()
        Renderer(backend).draw.circle(100, 200, 30, color=(0, 0, 255))
        self.assertEqual(backend.circles, [(100, 200, 30, (0, 0, 255, 255), True)])

    def test_circle_outline_mode(self):
        backend = StubRenderer()
        Renderer(backend).draw.circle(100, 200, 30, filled=False)
        self.assertEqual(backend.circles[0][4], False)

    def test_circle_rejects_invalid_radius(self):
        draw = _draw()
        for bad in (0, -1, True, 2.5):
            with self.assertRaises(ConfigurationError):
                draw.circle(0, 0, bad)

    def test_draw_commands_is_exposed_on_renderer(self):
        renderer = Renderer(StubRenderer())
        self.assertIsInstance(renderer.draw, DrawCommands)


class TestHeadlessDrawing(unittest.TestCase):
    def test_drawing_works_with_null_backend(self):
        class DrawingGame(Game):
            def draw(self):
                self.renderer.draw.pixel(1, 1)
                self.renderer.draw.line(0, 0, 5, 5, color=(10, 10, 10))
                self.renderer.draw.rect(0, 0, 4, 4, color=(255, 255, 255))
                self.renderer.draw.circle(2, 2, 1, filled=False)

        game = DrawingGame(backend=NullBackend())
        game.background = (20, 20, 25)
        game.run(max_frames=3)
        self.assertTrue(game.window.closed)


if __name__ == "__main__":
    unittest.main()