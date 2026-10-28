"""Tests for the Part 12 Sprite transform support: rotation, origin, flip,
per-axis scale, parenting, tint, and backend forwarding."""

import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import ConfigurationError, Image, Renderer, Sprite, Transform2D, Vector2


class SpriteTransformTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "tile.bmp", bmp_bytes(16, 16))
        self.backend = StubBackend(image_sizes={self._path: (16, 16)})
        self.renderer = Renderer(StubRenderer())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _image(self) -> Image:
        return Image(self._path, backend=self.backend)

    def _sprite(self) -> Sprite:
        return Sprite(self._image())


class TestSpriteTransformProperties(SpriteTransformTestBase):
    def test_rotation_default_and_setter(self):
        sprite = self._sprite()
        self.assertEqual(sprite.rotation, 0.0)
        sprite.rotation = 90
        self.assertEqual(sprite.rotation, 90.0)
        with self.assertRaises(ConfigurationError):
            sprite.rotation = "steep"

    def test_origin(self):
        sprite = self._sprite()
        self.assertEqual(sprite.origin, (0.0, 0.0))
        sprite.origin = (0.5, 0.5)
        self.assertEqual(sprite.origin, (0.5, 0.5))
        with self.assertRaises(ConfigurationError):
            sprite.origin = (0.5,)

    def test_flip_flags(self):
        sprite = self._sprite()
        self.assertFalse(sprite.flip_x)
        self.assertFalse(sprite.flip_y)
        sprite.flip_x = True
        sprite.flip_y = True
        self.assertTrue(sprite.flip_x)
        self.assertTrue(sprite.flip_y)
        with self.assertRaises(ConfigurationError):
            sprite.flip_x = 1
        with self.assertRaises(ConfigurationError):
            sprite.flip_y = "yes"

    def test_per_axis_scale(self):
        sprite = self._sprite()
        sprite.scale = (2, 1)
        self.assertEqual(sprite.scale, (2.0, 1.0))
        self.assertEqual(sprite.scale_x, 2.0)
        self.assertEqual(sprite.scale_y, 1.0)
        sprite.scale = 1.5
        self.assertEqual(sprite.scale, 1.5)

    def test_z(self):
        sprite = self._sprite()
        self.assertEqual(sprite.z, 0)
        sprite.z = 5
        self.assertEqual(sprite.z, 5)
        sprite.z = -2
        self.assertEqual(sprite.z, -2)
        with self.assertRaises(ConfigurationError):
            sprite.z = "top"

    def test_tint(self):
        sprite = self._sprite()
        self.assertEqual(sprite.tint, (255, 255, 255))
        sprite.tint = (255, 0, 0)
        self.assertEqual(sprite.tint, (255, 0, 0))
        with self.assertRaises(ConfigurationError):
            sprite.tint = (999, 0, 0)
        with self.assertRaises(ConfigurationError):
            sprite.tint = (1, 2)


class TestSpriteParenting(SpriteTransformTestBase):
    def test_parent_transform_world_position(self):
        parent = Transform2D(position=(100, 50))
        sprite = self._sprite()
        sprite.parent = parent
        sprite.x = 10
        sprite.y = 20
        self.assertEqual(sprite.world_position, Vector2(110, 70))
        parent.position = (200, 80)
        self.assertEqual(sprite.world_position, Vector2(210, 100))
        self.assertEqual(sprite.local_position, (10, 20))

    def test_parent_sprite_world_position(self):
        parent = self._sprite()
        parent.position = (100, 100)
        child = self._sprite()
        child.position = (10, 10)
        child.parent = parent
        self.assertEqual(child.world_position, Vector2(110, 110))
        parent.position = (300, 200)
        self.assertEqual(child.world_position, Vector2(310, 210))

    def test_world_rotation(self):
        parent = Transform2D(rotation=45)
        sprite = self._sprite()
        sprite.rotation = 10
        sprite.parent = parent
        self.assertEqual(sprite.world_rotation, 55.0)
        self.assertEqual(sprite.local_rotation, 10.0)

    def test_world_scale(self):
        parent = Transform2D(scale=2)
        sprite = self._sprite()
        sprite.scale = 1.5
        sprite.parent = parent
        self.assertEqual(sprite.world_scale, 3.0)
        self.assertEqual(sprite.local_scale, 1.5)

    def test_world_scale_tuple(self):
        parent = Transform2D(scale=(2, 3))
        sprite = self._sprite()
        sprite.parent = parent
        self.assertEqual(sprite.world_scale, (2.0, 3.0))

    def test_none_clears_parent(self):
        parent = Transform2D(position=(50, 50))
        sprite = self._sprite()
        sprite.parent = parent
        sprite.parent = None
        self.assertIsNone(sprite.parent)
        self.assertEqual(sprite.world_position, Vector2(0, 0))

    def test_invalid_parent(self):
        sprite = self._sprite()
        with self.assertRaises(ConfigurationError):
            sprite.parent = 42


class TestSpriteTransformDrawing(SpriteTransformTestBase):
    def test_plain_sprite_uses_plain_draw(self):
        sprite = self._sprite()
        sprite.draw(self.renderer)
        self.assertEqual(len(self.renderer._renderer.texture_draws), 1)
        self.assertEqual(len(self.renderer._renderer.transformed_draws), 0)

    def test_rotation_origin_flip_forwarded(self):
        sprite = self._sprite()
        sprite.rotation = 90
        sprite.origin = (0.5, 0.5)
        sprite.flip_x = True
        sprite.draw(self.renderer)
        self.assertEqual(len(self.renderer._renderer.transformed_draws), 1)
        texture, src, dst, alpha, angle, center, flip, color_mod = (
            self.renderer._renderer.transformed_draws[0]
        )
        self.assertEqual(angle, 90.0)
        self.assertEqual(center, (8, 8))  # 0.5 * 16
        self.assertEqual(flip, 1)
        self.assertEqual(color_mod, (255, 255, 255))
        self.assertEqual(alpha, 255)
        self.assertIsNone(src)

    def test_flip_y_bitmask(self):
        sprite = self._sprite()
        sprite.flip_x = True
        sprite.flip_y = True
        sprite.rotation = 5
        sprite.draw(self.renderer)
        _, _, _, _, _, _, flip, _ = self.renderer._renderer.transformed_draws[0]
        self.assertEqual(flip, 3)

    def test_tint_forwarded_as_color_mod(self):
        sprite = self._sprite()
        sprite.tint = (255, 0, 0)
        sprite.draw(self.renderer)
        _, _, _, _, _, _, _, color_mod = (
            self.renderer._renderer.transformed_draws[0]
        )
        self.assertEqual(color_mod, (255, 0, 0))

    def test_non_uniform_scale_uses_plain_draw(self):
        sprite = self._sprite()
        sprite.scale = (2, 1)
        sprite.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (0, 0, 32, 16))

    def test_origin_offsets_destination(self):
        sprite = self._sprite()
        sprite.position = (50, 60)
        sprite.origin = (1.0, 0.5)
        sprite.rotation = 15
        sprite.draw(self.renderer)
        _, _, dst, _, _, center, _, _ = self.renderer._renderer.transformed_draws[0]
        self.assertEqual(dst, (50 - 16, 60 - 8, 16, 16))
        self.assertEqual(center, (16, 8))

    def test_parent_moves_draw_position(self):
        parent = Transform2D(position=(100, 50))
        sprite = self._sprite()
        sprite.parent = parent
        sprite.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (100, 50, 16, 16))

    def test_animation_draw_keeps_transforms(self):
        from pydex_ge import Animation

        frames = [self._sprite(), self._sprite()]
        animation = Animation(frames, fps=2)
        sprite = self._sprite()
        sprite.animation = animation
        sprite.rotation = 45
        sprite.flip_x = True
        sprite.update(0.5)
        sprite.draw(self.renderer)
        self.assertTrue(self.renderer._renderer.transformed_draws)
        _, _, _, _, angle, _, flip, _ = self.renderer._renderer.transformed_draws[0]
        self.assertEqual(angle, 45.0)
        self.assertEqual(flip, 1)


class TestSpriteEffects(SpriteTransformTestBase):
    def test_fade_to(self):
        sprite = self._sprite()
        sprite.fade_to(0, 1.0)
        sprite.update(0.25)
        self.assertGreater(sprite.alpha, 0)
        sprite.update(0.75)
        self.assertEqual(sprite.alpha, 0)

    def test_flash(self):
        sprite = self._sprite()
        self.assertFalse(sprite.flashing)
        self.assertEqual(sprite.flash_strength, 0.0)
        sprite.flash(1.0)
        self.assertTrue(sprite.flashing)
        self.assertEqual(sprite.flash_strength, 1.0)
        sprite.update(0.5)
        self.assertAlmostEqual(sprite.flash_strength, 0.5)
        sprite.update(0.5)
        self.assertFalse(sprite.flashing)
        self.assertEqual(sprite.flash_strength, 0.0)

    def test_fade_to_validation(self):
        sprite = self._sprite()
        with self.assertRaises(ConfigurationError):
            sprite.fade_to(300, 1.0)
        with self.assertRaises(ConfigurationError):
            sprite.fade_to(0, 0)
        with self.assertRaises(ConfigurationError):
            sprite.fade_to(0, "soon")


if __name__ == "__main__":
    unittest.main()
