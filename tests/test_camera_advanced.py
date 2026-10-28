"""Tests for the Part 12 Camera additions: dead zone and deterministic shake."""

import unittest

from _stub_backend import StubRenderer

from pydex_ge import Camera, Camera2D, ConfigurationError, Renderer, Vector2


class _Target:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)


class TestCameraDeadZone(unittest.TestCase):
    def setUp(self) -> None:
        self.camera = Camera(width=800, height=600, position=(0, 0), zoom=1.0)
        self.target = _Target()

    def test_default_no_dead_zone(self):
        self.assertIsNone(self.camera.dead_zone)
        self.camera.follow(self.target, smoothing=0)
        self.target.x = 10
        self.camera.update(1 / 60)
        self.assertEqual(self.camera.position, Vector2(10, 0))

    def test_inside_zone_no_movement(self):
        self.camera.dead_zone = (100, 100)
        self.camera.follow(self.target, smoothing=0)
        self.target.x = 40  # inside half-width (50)
        self.camera.update(1 / 60)
        self.assertEqual(self.camera.position, Vector2(0, 0))

    def test_outside_zone_follows(self):
        self.camera.dead_zone = (100, 100)
        self.camera.follow(self.target, smoothing=0)
        self.target.x = 60  # 10 past half-width (50)
        self.camera.update(1 / 60)
        self.assertEqual(self.camera.position, Vector2(10, 0))

    def test_vertical_zone(self):
        self.camera.dead_zone = (0, 100)
        self.camera.follow(self.target, smoothing=0)
        self.target.y = 40
        self.camera.update(1 / 60)
        self.assertEqual(self.camera.position, Vector2(0, 0))
        self.target.y = 60
        self.camera.update(1 / 60)
        self.assertEqual(self.camera.position, Vector2(0, 10))

    def test_dead_zone_with_smoothing_still_eases(self):
        self.camera.dead_zone = (100, 100)
        self.camera.follow(self.target, smoothing=2.0)
        self.target.x = 1000
        self.camera.update(0.1)
        moved = self.camera.position.x
        self.assertGreater(moved, 0)
        self.assertLess(moved, 1000)

    def test_setting_none_disables(self):
        self.camera.dead_zone = (100, 100)
        self.camera.dead_zone = None
        self.assertIsNone(self.camera.dead_zone)

    def test_invalid_dead_zone(self):
        with self.assertRaises(ConfigurationError):
            self.camera.dead_zone = (100,)
        with self.assertRaises(ConfigurationError):
            self.camera.dead_zone = (-5, 10)
        with self.assertRaises(ConfigurationError):
            self.camera.dead_zone = (10, "big")


class TestCameraShake(unittest.TestCase):
    def setUp(self) -> None:
        self.camera = Camera(width=800, height=600, position=(0, 0), zoom=1.0)

    def test_idle_offset_is_zero(self):
        self.assertEqual(self.camera.shake_offset, (0.0, 0.0))
        self.assertFalse(self.camera.shaking)

    def test_shake_activates(self):
        self.camera.shake(10, 1.0)
        self.assertTrue(self.camera.shaking)
        self.assertEqual(self.camera.shake_offset, (0.0, 0.0))
        self.camera.update(0.1)
        self.assertNotEqual(self.camera.shake_offset, (0.0, 0.0))

    def test_shake_ends_exactly_at_zero(self):
        self.camera.shake(10, 1.0)
        self.camera.update(0.5)
        self.camera.update(0.6)  # total 1.1 > 1.0
        self.assertFalse(self.camera.shaking)
        self.assertEqual(self.camera.shake_offset, (0.0, 0.0))

    def test_shake_is_deterministic(self):
        first = Camera(width=800, height=600)
        second = Camera(width=800, height=600)
        first.shake(8, 1.0)
        second.shake(8, 1.0)
        for _ in range(5):
            first.update(0.1)
            second.update(0.1)
        self.assertEqual(first.shake_offset, second.shake_offset)

    def test_new_shake_replaces_old(self):
        original = Camera(width=800, height=600)
        replaced = Camera(width=800, height=600)
        original.shake(8, 1.0)
        replaced.shake(8, 1.0)
        original.update(0.3)
        replaced.update(0.3)
        original.shake(4, 0.5)
        replaced.shake(4, 0.5)
        original.update(0.2)
        replaced.update(0.2)
        self.assertEqual(original.shake_offset, replaced.shake_offset)

    def test_duration_zero_is_noop(self):
        self.camera.shake(10, 0)
        self.assertFalse(self.camera.shaking)
        self.assertEqual(self.camera.shake_offset, (0.0, 0.0))

    def test_shake_validation(self):
        with self.assertRaises(ConfigurationError):
            self.camera.shake(-1, 1.0)
        with self.assertRaises(ConfigurationError):
            self.camera.shake(1, -1.0)
        with self.assertRaises(ConfigurationError):
            self.camera.shake("big", 1.0)
        with self.assertRaises(ConfigurationError):
            self.camera.shake(1.0, "long")

    def test_world_screen_roundtrip_with_shake(self):
        self.camera.shake(10, 1.0)
        self.camera.update(0.3)
        dx, dy = self.camera.shake_offset
        screen = self.camera.world_to_screen((self.camera.x, self.camera.y))
        self.assertAlmostEqual(screen.x, 400 + dx)
        self.assertAlmostEqual(screen.y, 300 + dy)
        back = self.camera.screen_to_world(screen)
        self.assertAlmostEqual(back.x, self.camera.x, places=6)
        self.assertAlmostEqual(back.y, self.camera.y, places=6)

    def test_shake_offset_visual_only(self):
        self.camera.shake(10, 1.0)
        self.camera.update(0.2)
        self.assertEqual(self.camera.position, Vector2(0, 0))


class TestActiveCamera(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = Renderer(StubRenderer())

    def test_active_camera_stack(self):
        camera = Camera(width=800, height=600)
        self.assertIsNone(self.renderer.active_camera)
        self.renderer.begin_camera(camera)
        self.assertIs(self.renderer.active_camera, camera)
        self.renderer.end_camera()
        self.assertIsNone(self.renderer.active_camera)

    def test_topmost_camera_wins(self):
        outer = Camera(width=800, height=600)
        inner = Camera(width=400, height=300)
        self.renderer.begin_camera(outer)
        self.renderer.begin_camera(inner)
        self.assertIs(self.renderer.active_camera, inner)
        self.renderer.end_camera()
        self.assertIs(self.renderer.active_camera, outer)
        self.renderer.end_camera()


class TestCamera2DAdvanced(unittest.TestCase):
    def test_camera2d_supports_shake_and_dead_zone(self):
        camera = Camera2D(position=(10, 10))
        camera.shake(5, 0.5)
        camera.update(0.1)
        self.assertTrue(camera.shaking)
        camera.dead_zone = (50, 50)
        self.assertEqual(camera.dead_zone, (50, 50))


if __name__ == "__main__":
    unittest.main()
