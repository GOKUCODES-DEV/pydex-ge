"""Tests for Camera / Camera2D: math, following, bounds, and renderer integration."""

import os
import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import (
    Animation,
    Body,
    Camera,
    Camera2D,
    ConfigurationError,
    Image,
    Label,
    Rect,
    Renderer,
    Sprite,
    SpriteSheet,
    Vector2,
)


class _Positional:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class CameraTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "tile.bmp", bmp_bytes(16, 16))
        self._font_path = os.path.join(self._tmp.name, "font.ttf")
        with open(self._font_path, "wb") as handle:
            handle.write(b"\x00\x01\x00\x00 fake ttf bytes")
        self.backend = StubBackend(image_sizes={self._path: (16, 16)})
        self.renderer = Renderer(StubRenderer())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _image(self) -> Image:
        return Image(self._path, backend=self.backend)

    def _sprite(self) -> Sprite:
        return Sprite(self._image())


class TestCameraConstruction(CameraTestBase):
    def test_defaults(self):
        camera = Camera()
        self.assertEqual(camera.width, 800)
        self.assertEqual(camera.height, 600)
        self.assertEqual(camera.position, Vector2(0.0, 0.0))
        self.assertEqual(camera.zoom, 1.0)
        self.assertTrue(camera.enabled)
        self.assertIsNone(camera.bounds)
        self.assertEqual(camera.viewport, Rect(0, 0, 800, 600))

    def test_position_and_zoom(self):
        camera = Camera(position=(100, 50), zoom=2.0)
        self.assertEqual(camera.position, Vector2(100, 50))
        self.assertEqual(camera.zoom, 2.0)

    def test_invalid_width_rejected(self):
        for bad in (0, -1, True, "x"):
            with self.assertRaises(ConfigurationError):
                Camera(bad)

    def test_invalid_height_rejected(self):
        for bad in (0, -1, True, "x"):
            with self.assertRaises(ConfigurationError):
                Camera(800, bad)

    def test_invalid_zoom_rejected(self):
        for bad in (0, -1, True, "x"):
            with self.assertRaises(ConfigurationError):
                Camera(zoom=bad)

    def test_invalid_position_rejected(self):
        with self.assertRaises(ConfigurationError):
            Camera(position=123)

    def test_camera2d_is_usable_camera(self):
        camera = Camera2D(position=(1, 2), zoom=1.5)
        self.assertIsInstance(camera, Camera)
        self.assertEqual(camera.position, Vector2(1, 2))
        self.assertEqual(camera.zoom, 1.5)


class TestCameraPosition(CameraTestBase):
    def test_position_assignment(self):
        camera = Camera()
        camera.position = (100, 200)
        self.assertEqual(camera.position, Vector2(100, 200))

    def test_position_assignment_vector(self):
        camera = Camera()
        camera.position = Vector2(5, 6)
        self.assertEqual(camera.position, Vector2(5, 6))

    def test_x_y_set(self):
        camera = Camera()
        camera.x = 5
        camera.y = 6
        self.assertEqual(camera.position, Vector2(5, 6))

    def test_x_y_bad_rejected(self):
        camera = Camera()
        for bad in (True, "x"):
            with self.assertRaises(ConfigurationError):
                camera.x = bad
            with self.assertRaises(ConfigurationError):
                camera.y = bad

    def test_move(self):
        camera = Camera(position=(10, 20))
        camera.move(5, -3)
        self.assertEqual(camera.position, Vector2(15, 17))

    def test_move_bad_rejected(self):
        camera = Camera()
        with self.assertRaises(ConfigurationError):
            camera.move(True, 0)

    def test_look_at(self):
        camera = Camera()
        camera.look_at((50, 60))
        self.assertEqual(camera.position, Vector2(50, 60))

    def test_zoom_settable(self):
        camera = Camera()
        camera.zoom = 2.0
        camera.zoom = 0.5
        camera.zoom = 1.0
        self.assertEqual(camera.zoom, 1.0)

    def test_zoom_invalid_rejected(self):
        camera = Camera()
        for bad in (0, -1, True, "x"):
            with self.assertRaises(ConfigurationError):
                camera.zoom = bad

    def test_enabled_settable(self):
        camera = Camera()
        camera.enabled = False
        self.assertFalse(camera.enabled)
        with self.assertRaises(ConfigurationError):
            camera.enabled = 1


class TestCameraConversion(CameraTestBase):
    def test_world_to_screen_center(self):
        camera = Camera(800, 600, position=(100, 50))
        screen = camera.world_to_screen((100, 50))
        self.assertEqual(screen, Vector2(400, 300))

    def test_world_to_screen_offset(self):
        camera = Camera(800, 600, position=(100, 50))
        screen = camera.world_to_screen((200, 100))
        self.assertEqual(screen, Vector2(500, 350))

    def test_screen_to_world(self):
        camera = Camera(800, 600, position=(100, 50))
        world = camera.screen_to_world((500, 350))
        self.assertEqual(world, Vector2(200, 100))

    def test_round_trip_world(self):
        camera = Camera(640, 480, position=(123.4, -56.7), zoom=1.3)
        point = Vector2(400.25, 99.75)
        result = camera.screen_to_world(camera.world_to_screen(point))
        self.assertAlmostEqual(result.x, point.x, places=6)
        self.assertAlmostEqual(result.y, point.y, places=6)

    def test_round_trip_screen(self):
        camera = Camera(640, 480, position=(123.4, -56.7), zoom=0.7)
        point = Vector2(210, 330)
        result = camera.world_to_screen(camera.screen_to_world(point))
        self.assertAlmostEqual(result.x, point.x, places=6)
        self.assertAlmostEqual(result.y, point.y, places=6)

    def test_zoom_affects_conversion(self):
        camera = Camera(800, 600, position=(0, 0), zoom=2.0)
        screen = camera.world_to_screen((100, 50))
        self.assertEqual(screen, Vector2(600, 400))

    def test_zoom_affects_inverse(self):
        camera = Camera(800, 600, position=(0, 0), zoom=2.0)
        world = camera.screen_to_world((600, 400))
        self.assertEqual(world, Vector2(100, 50))

    def test_returns_vector2(self):
        camera = Camera()
        self.assertIsInstance(camera.world_to_screen((0, 0)), Vector2)
        self.assertIsInstance(camera.screen_to_world((0, 0)), Vector2)

    def test_bad_input_rejected(self):
        camera = Camera()
        for bad in (123, "x", (1,)):
            with self.assertRaises(ConfigurationError):
                camera.world_to_screen(bad)
            with self.assertRaises(ConfigurationError):
                camera.screen_to_world(bad)


class TestCameraFollowing(CameraTestBase):
    def test_follow_vector2(self):
        camera = Camera()
        camera.follow(Vector2(10, 20))
        camera.update(0.1)
        self.assertEqual(camera.position, Vector2(10, 20))

    def test_follow_tuple(self):
        camera = Camera()
        camera.follow((30, 40))
        camera.update(0.1)
        self.assertEqual(camera.position, Vector2(30, 40))

    def test_follow_body_tracks_movement(self):
        camera = Camera()
        body = Body(position=(5, 5))
        camera.follow(body)
        body.position = (7, 8)
        camera.update(0.1)
        self.assertEqual(camera.position, Vector2(7, 8))

    def test_follow_x_y_object(self):
        camera = Camera()
        target = _Positional(3, 4)
        camera.follow(target)
        target.x = 9
        target.y = 1
        camera.update(0.1)
        self.assertEqual(camera.position, Vector2(9, 1))

    def test_follow_invalid_target_rejected(self):
        camera = Camera()
        for bad in (123, "sprite", None):
            with self.assertRaises(ConfigurationError):
                camera.follow(bad)

    def test_clear_target(self):
        camera = Camera()
        camera.follow(Vector2(50, 60))
        camera.update(0.1)
        camera.clear_target()
        camera.update(0.1)
        self.assertEqual(camera.position, Vector2(50, 60))

    def test_clear_follow_alias(self):
        camera = Camera()
        camera.follow(Vector2(50, 60))
        camera.clear_follow()
        camera.update(0.1)
        self.assertEqual(camera.position, Vector2(0, 0))

    def test_smoothing_zero_snaps(self):
        camera = Camera()
        camera.follow(Vector2(100, 0), smoothing=0)
        camera.update(1.0)
        self.assertEqual(camera.position, Vector2(100, 0))

    def test_smoothing_gradual(self):
        camera = Camera(position=(0, 0))
        camera.follow(Vector2(100, 0), smoothing=5)
        camera.update(0.1)
        self.assertGreater(camera.position.x, 0)
        self.assertLess(camera.position.x, 100)
        self.assertEqual(camera.position.y, 0)

    def test_smoothing_approaches_target(self):
        camera = Camera(position=(0, 0))
        camera.follow(Vector2(100, 0), smoothing=5)
        for _ in range(200):
            camera.update(0.016)
        self.assertAlmostEqual(camera.position.x, 100, delta=0.5)

    def test_smoothing_setter(self):
        camera = Camera()
        camera.smoothing = 3.0
        self.assertEqual(camera.smoothing, 3.0)
        for bad in (-1, True, "x"):
            with self.assertRaises(ConfigurationError):
                camera.smoothing = bad

    def test_update_negative_dt_rejected(self):
        camera = Camera()
        with self.assertRaises(ConfigurationError):
            camera.update(-1)

    def test_update_bool_dt_rejected(self):
        camera = Camera()
        with self.assertRaises(ConfigurationError):
            camera.update(True)


class TestCameraBounds(CameraTestBase):
    def test_bounds_clamp(self):
        camera = Camera(200, 200, position=(50, 50))
        camera.bounds = Rect(0, 0, 1000, 1000)
        camera.update(0)
        self.assertEqual(camera.position, Vector2(100, 100))

    def test_bounds_allows_inside(self):
        camera = Camera(200, 200, position=(500, 500))
        camera.bounds = Rect(0, 0, 1000, 1000)
        camera.update(0)
        self.assertEqual(camera.position, Vector2(500, 500))

    def test_bounds_keeps_camera_inside(self):
        camera = Camera(200, 200, position=(950, 50))
        camera.bounds = Rect(0, 0, 1000, 1000)
        camera.update(0)
        self.assertEqual(camera.position, Vector2(900, 100))

    def test_small_world_centered(self):
        camera = Camera(800, 600, position=(0, 0))
        camera.bounds = Rect(0, 0, 100, 100)
        camera.update(0)
        self.assertEqual(camera.position, Vector2(50, 50))

    def test_bounds_with_zoom(self):
        camera = Camera(400, 300, position=(1000, 1000), zoom=2.0)
        camera.bounds = Rect(0, 0, 1000, 1000)
        camera.update(0)
        self.assertEqual(camera.position, Vector2(900, 925))

    def test_bounds_invalid_rejected(self):
        camera = Camera()
        with self.assertRaises(ConfigurationError):
            camera.bounds = (0, 0, 100, 100)

    def test_bounds_none_clears(self):
        camera = Camera()
        camera.bounds = Rect(0, 0, 100, 100)
        camera.bounds = None
        camera.update(0)
        self.assertIsNone(camera.bounds)


class TestCameraRendererIntegration(CameraTestBase):
    def test_begin_end_transforms_sprite(self):
        sprite = self._sprite()
        sprite.position = (10, 20)
        camera = Camera(800, 600, position=(10, 20))
        camera.begin(self.renderer)
        self.renderer.draw_sprite(sprite)
        camera.end()
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (400, 300, 16, 16))

    def test_zoom_scales_world_size(self):
        sprite = self._sprite()
        sprite.position = (10, 20)
        camera = Camera(800, 600, position=(10, 20), zoom=2.0)
        camera.begin(self.renderer)
        self.renderer.draw_sprite(sprite)
        camera.end()
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (400, 300, 32, 32))

    def test_end_restores_untransformed_drawing(self):
        sprite = self._sprite()
        sprite.position = (10, 20)
        camera = Camera(800, 600, position=(10, 20))
        camera.begin(self.renderer)
        camera.end()
        self.renderer.draw_sprite(sprite)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (10, 20, 16, 16))

    def test_camera_stack_pushes_and_pops(self):
        camera = Camera()
        camera.begin(self.renderer)
        self.assertEqual(len(self.renderer._camera_stack), 1)
        camera.end()
        self.assertEqual(self.renderer._camera_stack, [])

    def test_begin_without_renderer_raises(self):
        camera = Camera()
        with self.assertRaises(ConfigurationError):
            camera.begin()

    def test_attach_allows_argless_begin(self):
        camera = Camera()
        camera.attach(self.renderer)
        camera.begin()
        camera.end()

    def test_end_without_begin_raises(self):
        camera = Camera()
        with self.assertRaises(ConfigurationError):
            camera.end()

    def test_disabled_camera_begin_is_noop(self):
        sprite = self._sprite()
        sprite.position = (10, 20)
        camera = Camera(800, 600, position=(10, 20))
        camera.enabled = False
        camera.begin(self.renderer)
        self.renderer.draw_sprite(sprite)
        camera.end()
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (10, 20, 16, 16))

    def test_label_remains_screen_space(self):
        label = Label("HI", font=self._font_path, position=(5, 6), backend=self.backend)
        camera = Camera(800, 600, position=(400, 300))
        camera.begin(self.renderer)
        self.renderer.draw_label(label)
        camera.end()
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual((dst[0], dst[1]), (5, 6))

    def test_sprite_animation_camera_renderer_integration(self):
        sheet = SpriteSheet(self._image(), 8, 8)
        animation = Animation([sheet.cell(0, 0), sheet.cell(1, 0)], fps=10)
        sprite = self._sprite()
        sprite.animation = animation
        sprite.play()
        sprite.position = (10, 20)

        camera = Camera(800, 600, position=(10, 20))
        camera.begin(self.renderer)
        sprite.draw(self.renderer)
        camera.end()
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(src, (0, 0, 8, 8))
        self.assertEqual(dst, (400, 300, 8, 8))

        sprite.update(0.1)
        camera.begin(self.renderer)
        sprite.draw(self.renderer)
        camera.end()
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[1]
        self.assertEqual(src, (8, 0, 8, 8))
        self.assertEqual(dst, (400, 300, 8, 8))


if __name__ == "__main__":
    unittest.main()
