"""Tests for Sprite behavior and drawing dispatch (headless)."""

import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import ConfigurationError, Image, Renderer, Sprite, Transform2D, Vector2


class SpriteTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "tile.bmp", bmp_bytes(16, 16))
        self.backend = StubBackend(image_sizes={self._path: (16, 16)})
        self.renderer = Renderer(StubRenderer())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _image(self) -> Image:
        return Image(self._path, backend=self.backend)


class TestSpriteConstruction(SpriteTestBase):
    def test_from_path(self):
        sprite = Sprite(self._path, backend=self.backend)
        self.assertEqual((sprite.width, sprite.height), (16, 16))
        self.assertEqual(sprite.position, (0, 0))

    def test_from_image(self):
        sprite = Sprite(self._image())
        self.assertEqual((sprite.width, sprite.height), (16, 16))

    def test_defaults(self):
        sprite = Sprite(self._image())
        self.assertEqual(sprite.scale, 1.0)
        self.assertEqual(sprite.alpha, 255)
        self.assertTrue(sprite.visible)
        self.assertEqual(sprite.position, (0, 0))

    def test_empty_path_rejected(self):
        with self.assertRaises(ConfigurationError):
            Sprite("   ")

    def test_bad_source_rejected(self):
        for source in (None, 123, 4.5):
            with self.assertRaises(ConfigurationError):
                Sprite(source)


class TestSpriteState(SpriteTestBase):
    def test_position_setter(self):
        sprite = Sprite(self._image())
        sprite.position = (10, 20)
        self.assertEqual((sprite.x, sprite.y), (10, 20))
        self.assertEqual(sprite.position, (10, 20))

    def test_x_y_assignable(self):
        sprite = Sprite(self._image())
        sprite.x, sprite.y = 5, 7
        self.assertEqual(sprite.position, (5, 7))

    def test_bad_position_rejected(self):
        sprite = Sprite(self._image())
        for bad in ((1.5, 0), (True, 0), (0, "x")):
            with self.assertRaises(ConfigurationError):
                sprite.position = bad

    def test_scale_validation(self):
        sprite = Sprite(self._image())
        sprite.scale = 0.5
        self.assertEqual(sprite.scale, 0.5)
        for bad in (0, -1, True, "big"):
            with self.assertRaises(ConfigurationError):
                sprite.scale = bad

    def test_alpha_validation(self):
        sprite = Sprite(self._image())
        sprite.alpha = 128
        self.assertEqual(sprite.alpha, 128)
        for bad in (-1, 256, 1.5, True):
            with self.assertRaises(ConfigurationError):
                sprite.alpha = bad

    def test_visible_flag(self):
        sprite = Sprite(self._image())
        sprite.visible = False
        self.assertFalse(sprite.visible)


class TestPixelSprites(SpriteTestBase):
    def test_from_pixels_dimensions(self):
        pixels = bytes(4 * 4 * 4)
        sprite = Sprite.from_pixels(4, 4, pixels)
        self.assertEqual((sprite.width, sprite.height), (4, 4))

    def test_from_pixels_bad_length_rejected(self):
        with self.assertRaises(ConfigurationError):
            Sprite.from_pixels(4, 4, bytes(15))

    def test_from_pixels_bad_dimensions_rejected(self):
        with self.assertRaises(ConfigurationError):
            Sprite.from_pixels(0, 4, bytes(0))

    def test_pixel_sprite_draws(self):
        pixels = bytes(range(64))
        sprite = Sprite.from_pixels(4, 4, pixels)
        sprite.position = (50, 60)
        sprite.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(texture.pixels, pixels)
        self.assertIsNone(src)
        self.assertEqual(dst, (50, 60, 4, 4))
        self.assertEqual(alpha, 255)


class TestSpriteDrawing(SpriteTestBase):
    def test_image_sprite_draws_full(self):
        sprite = Sprite(self._image())
        self.renderer.draw_sprite(sprite)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertIsNone(src)
        self.assertEqual(dst, (0, 0, 16, 16))
        self.assertEqual(alpha, 255)

    def test_position_scale_alpha_forwarded(self):
        sprite = Sprite(self._image())
        sprite.position = (10, 20)
        sprite.scale = 2.0
        sprite.alpha = 128
        self.renderer.draw_sprite(sprite)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (10, 20, 32, 32))
        self.assertEqual(alpha, 128)

    def test_fractional_scale_rounds(self):
        sprite = Sprite(self._image())
        sprite.scale = 1.5
        self.renderer.draw_sprite(sprite)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (0, 0, 24, 24))

    def test_region_sprite_sends_src_rect(self):
        sprite = Sprite(self._image(), region=(4, 4, 8, 8))
        sprite.scale = 2.0
        self.renderer.draw_sprite(sprite)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(src, (4, 4, 8, 8))
        self.assertEqual(dst, (0, 0, 16, 16))

    def test_region_outside_image_rejected(self):
        with self.assertRaises(ConfigurationError):
            Sprite(self._image(), region=(8, 8, 16, 16))

    def test_invisible_sprite_draws_nothing(self):
        sprite = Sprite(self._image())
        sprite.visible = False
        self.renderer.draw_sprite(sprite)
        self.assertEqual(self.renderer._renderer.texture_draws, [])

    def test_texture_cached_between_frames(self):
        sprite = Sprite(self._image())
        self.renderer.draw_sprite(sprite)
        self.renderer.draw_sprite(sprite)
        self.assertEqual(len(self.renderer._renderer.textures), 1)
        self.assertEqual(len(self.renderer._renderer.texture_draws), 2)


class TestSpriteValidationAndEffects(SpriteTestBase):
    def test_x_y_reject_non_numbers(self):
        sprite = Sprite(self._image())
        for bad in (True, "5", None):
            with self.assertRaises(ConfigurationError):
                sprite.x = bad
            with self.assertRaises(ConfigurationError):
                sprite.y = bad
        sprite.x = 1.5
        sprite.y = 2.0
        self.assertEqual(sprite.x, 1.5)
        self.assertEqual(sprite.y, 2)

    def test_z_preserves_integers_and_accepts_floats(self):
        sprite = Sprite(self._image())
        self.assertEqual(sprite.z, 0)
        sprite.z = 3
        self.assertEqual(sprite.z, 3)
        self.assertIsInstance(sprite.z, int)
        sprite.z = 2.5
        self.assertEqual(sprite.z, 2.5)
        self.assertIsInstance(sprite.z, float)

    def test_flash_tint_applied_immediately(self):
        sprite = Sprite(self._image())
        sprite.flash(1.0, (255, 0, 0))
        self.assertTrue(sprite.flashing)
        self.assertAlmostEqual(sprite.flash_strength, 1.0, places=6)
        self.assertEqual(sprite._draw_tint, (255, 0, 0))


class TestSpriteParenting(SpriteTestBase):
    def test_world_position_plain_translation(self):
        sprite = Sprite(self._image())
        parent = Transform2D(position=(50, 60))
        sprite.parent = parent
        sprite.position = (5, 6)
        self.assertEqual(sprite.world_position, Vector2(55, 66))

    def test_world_position_scales_and_rotates_offset(self):
        sprite = Sprite(self._image())
        parent = Transform2D(position=(100, 100), rotation=90, scale=2)
        sprite.parent = parent
        sprite.position = (10, 0)
        world = sprite.world_position
        self.assertAlmostEqual(world.x, 100.0, places=6)
        self.assertAlmostEqual(world.y, 120.0, places=6)


if __name__ == "__main__":
    unittest.main()