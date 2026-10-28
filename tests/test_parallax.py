"""Tests for the Part 12 Parallax background layer."""

import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import Camera, ConfigurationError, Parallax, Renderer, Sprite


class ParallaxTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "bg.bmp", bmp_bytes(32, 32))
        self.backend = StubBackend(image_sizes={self._path: (32, 32)})
        self.renderer = Renderer(StubRenderer())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _sprite(self) -> Sprite:
        return Sprite(self._path, backend=self.backend)


class TestParallaxConstruction(unittest.TestCase):
    def test_defaults(self):
        sprite = Sprite.from_pixels(1, 1, b"\xff\xff\xff\xff")
        parallax = Parallax(sprite)
        self.assertIs(parallax.sprite, sprite)
        self.assertEqual(parallax.factor, 0.25)

    def test_factor_pair(self):
        sprite = Sprite.from_pixels(1, 1, b"\xff\xff\xff\xff")
        parallax = Parallax(sprite, factor=(0.5, 0.1))
        self.assertEqual(parallax.factor, (0.5, 0.1))
        self.assertEqual(parallax.factor_x, 0.5)
        self.assertEqual(parallax.factor_y, 0.1)
        parallax.factor = 0.9
        self.assertEqual(parallax.factor, 0.9)
        parallax.factor = (1, 0)
        self.assertEqual(parallax.factor, (1.0, 0.0))

    def test_requires_sprite(self):
        with self.assertRaises(ConfigurationError):
            Parallax("not a sprite")
        with self.assertRaises(ConfigurationError):
            Parallax(None)

    def test_invalid_factor(self):
        sprite = Sprite.from_pixels(1, 1, b"\xff\xff\xff\xff")
        with self.assertRaises(ConfigurationError):
            Parallax(sprite, factor=(0.5, 0.5, 0.5))
        with self.assertRaises(ConfigurationError):
            Parallax(sprite, factor="slow")


class TestParallaxOffset(unittest.TestCase):
    def setUp(self) -> None:
        self.sprite = Sprite.from_pixels(1, 1, b"\xff\xff\xff\xff")
        self.camera = Camera(position=(100, 50))

    def test_factor_one_is_zero_offset(self):
        parallax = Parallax(self.sprite, factor=1.0)
        self.assertEqual(parallax.offset(self.camera), (0.0, 0.0))

    def test_factor_zero_is_full_camera(self):
        parallax = Parallax(self.sprite, factor=0.0)
        self.assertEqual(parallax.offset(self.camera), (100.0, 50.0))

    def test_half_factor(self):
        parallax = Parallax(self.sprite, factor=0.5)
        self.assertEqual(parallax.offset(self.camera), (50.0, 25.0))

    def test_per_axis_factor(self):
        parallax = Parallax(self.sprite, factor=(0.5, 0.0))
        self.assertEqual(parallax.offset(self.camera), (50.0, 50.0))

    def test_none_camera(self):
        parallax = Parallax(self.sprite, factor=0.5)
        self.assertEqual(parallax.offset(None), (0.0, 0.0))


class TestParallaxDraw(ParallaxTestBase):
    def test_draw_without_camera(self):
        parallax = Parallax(self._sprite(), factor=0.5)
        parallax.draw(self.renderer)
        self.assertEqual(len(self.renderer._renderer.texture_draws), 1)

    def test_draw_with_active_camera_offsets_position(self):
        camera = Camera(position=(100, 50))
        sprite = self._sprite()
        parallax = Parallax(sprite, factor=0.5)
        self.renderer.begin_camera(camera)
        try:
            parallax.draw(self.renderer)
        finally:
            self.renderer.end_camera()
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        # Sprite world pos (0,0) + offset (50, 25) -> world (50, 25)
        # screen = (50 - 100) + 400, (25 - 50) + 300 = (350, 275)
        self.assertEqual(dst, (350, 275, 32, 32))

    def test_draw_restores_sprite_position(self):
        camera = Camera(position=(100, 50))
        sprite = self._sprite()
        sprite.position = (10, 20)
        parallax = Parallax(sprite, factor=0.5)
        self.renderer.begin_camera(camera)
        try:
            parallax.draw(self.renderer)
        finally:
            self.renderer.end_camera()
        self.assertEqual(sprite.position, (10, 20))

    def test_draw_without_active_camera_keeps_position(self):
        sprite = self._sprite()
        sprite.position = (7, 9)
        parallax = Parallax(sprite, factor=0.5)
        parallax.draw(self.renderer)
        self.assertEqual(sprite.position, (7, 9))


if __name__ == "__main__":
    unittest.main()
