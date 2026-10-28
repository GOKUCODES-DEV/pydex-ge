"""Tests for the renderer's texture handling and texture regions."""

import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture

from pydex_ge import ConfigurationError, Image, Texture, TextureRegion
from pydex_ge.backend.null import NullBackend, NullRenderer
from pydex_ge.core.renderer import Renderer


class TextureTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "img.bmp", bmp_bytes(32, 24))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _image(self, width: int = 32, height: int = 24) -> Image:
        if (width, height) != (32, 24):
            self._path = write_fixture(
                self._tmp.name, "img.bmp", bmp_bytes(width, height)
            )
        return Image(self._path, backend=NullBackend())


class TestRendererTextures(TextureTestBase):
    def test_create_texture_from_image_reports_size(self):
        image = self._image(4, 3)
        renderer = Renderer(NullRenderer())
        texture = renderer.create_texture(image)
        self.assertIsInstance(texture, Texture)
        self.assertEqual((texture.width, texture.height), (4, 3))
        texture.destroy()
        image.destroy()

    def test_texture_cache_returns_same_instance(self):
        image = self._image()
        renderer = Renderer(NullRenderer())
        self.assertIs(renderer.create_texture(image), renderer.create_texture(image))
        image.destroy()

    def test_texture_usable_after_destroy(self):
        image = self._image()
        renderer = Renderer(NullRenderer())
        texture = renderer.create_texture(image)
        texture.destroy()
        with self.assertRaises(RuntimeError):
            texture.width
        image.destroy()

    def test_create_texture_requires_image(self):
        renderer = Renderer(NullRenderer())
        with self.assertRaises(TypeError):
            renderer.create_texture("player.png")

    def test_renderer_destroy_frees_textures(self):
        image = self._image()
        renderer = Renderer(NullRenderer())
        renderer.create_texture(image)
        renderer.destroy()
        with self.assertRaises(RuntimeError):
            renderer.create_texture(image)
        image.destroy()


class TestTextureRegion(TextureTestBase):
    def test_region_properties(self):
        image = self._image()
        region = TextureRegion(image, 5, 6, 20, 10)
        self.assertEqual(region.x, 5)
        self.assertEqual(region.y, 6)
        self.assertEqual((region.width, region.height), (20, 10))
        self.assertIs(region.image, image)

    def test_region_within_bounds_accepted(self):
        image = self._image()
        TextureRegion(image, 0, 0, image.width, image.height)

    def test_region_outside_bounds_rejected(self):
        image = self._image()
        for region in [
            (0, 0, image.width + 1, 1),
            (0, 0, 1, image.height + 1),
            (-1, 0, 10, 10),
            (0, 0, 0, 10),
        ]:
            with self.assertRaises(ConfigurationError):
                TextureRegion(image, *region)

    def test_region_sprite_shares_image(self):
        image = self._image()
        region = TextureRegion(image, 1, 1, 2, 2)
        sprite = region.sprite()
        self.assertIs(sprite._image, image)
        self.assertEqual((sprite.width, sprite.height), (2, 2))


if __name__ == "__main__":
    unittest.main()