"""Tests for the Part 3D Camera3D perspective projection and orientation."""

import unittest

from pydex_ge import Camera3D, ConfigurationError, Quaternion, Vector3


class TestCamera3DConstruction(unittest.TestCase):
    def test_defaults(self):
        c = Camera3D()
        self.assertIsNone(c.width)
        self.assertIsNone(c.height)
        self.assertEqual(c.position, Vector3(0, 0, 0))
        self.assertEqual(c.rotation, Quaternion.identity())
        self.assertEqual(c.fov, 60.0)
        self.assertEqual(c.near, 0.1)
        self.assertEqual(c.far, 1000.0)
        self.assertEqual(c.zoom, 1.0)
        self.assertTrue(c.enabled)

    def test_viewport(self):
        c = Camera3D(800, 600)
        self.assertEqual(c.width, 800.0)
        self.assertEqual(c.height, 600.0)
        self.assertAlmostEqual(c.aspect, 800.0 / 600.0)
        c.set_viewport(640, 480)
        self.assertEqual((c.width, c.height), (640.0, 480.0))

    def test_invalid_fov_near_far(self):
        with self.assertRaises(ConfigurationError):
            Camera3D(fov=0)
        with self.assertRaises(ConfigurationError):
            Camera3D(fov=200)
        with self.assertRaises(ConfigurationError):
            Camera3D(near=10, far=1)
        with self.assertRaises(ConfigurationError):
            Camera3D(near=0, far=10)
        with self.assertRaises(ConfigurationError):
            Camera3D(zoom=0)

    def test_project_without_viewport_raises(self):
        c = Camera3D()
        with self.assertRaises(ConfigurationError):
            c.project((0, 0, -5))


class TestCamera3DProjection(unittest.TestCase):
    def setUp(self):
        self.camera = Camera3D(800, 600)
        self.camera.set_viewport(800, 600)

    def test_center_projection(self):
        sx, sy, depth = self.camera.project((0, 0, -5))
        self.assertAlmostEqual(sx, 400.0)
        self.assertAlmostEqual(sy, 300.0)
        self.assertAlmostEqual(depth, 5.0)

    def test_depth_equals_camera_z_distance(self):
        _, _, depth = self.camera.project((1, 2, -7))
        self.assertAlmostEqual(depth, 7.0)

    def test_behind_camera_is_none(self):
        self.assertIsNone(self.camera.project((0, 0, 5)))

    def test_beyond_far_is_none(self):
        self.assertIsNone(self.camera.project((0, 0, -2000)))

    def test_beyond_near_is_none(self):
        self.assertIsNone(self.camera.project((0, 0, -0.05)))

    def test_zoom_magnifies(self):
        self.camera.zoom = 2.0
        sx, sy, _ = self.camera.project((1, 0, -5))
        self.assertGreater(sx, 400.0)

    def test_fov_widening_brings_points_closer(self):
        normal, _, _ = self.camera.project((1, 0, -5))
        self.camera.fov = 120
        wide, _, _ = self.camera.project((1, 0, -5))
        self.assertLess(abs(wide - 400.0), abs(normal - 400.0))

    def test_position_offsets_projection(self):
        self.camera.position = (10, 0, 0)
        sx, _, _ = self.camera.project((10, 0, -5))
        self.assertAlmostEqual(sx, 400.0)


class TestCamera3DOrientation(unittest.TestCase):
    def setUp(self):
        self.camera = Camera3D(800, 600)
        self.camera.set_viewport(800, 600)

    def test_identity_forward(self):
        self.assertEqual(self.camera.forward, Vector3(0, 0, -1))

    def test_look_at_forward(self):
        self.camera.look_at((10, 0, 0))
        self.assertAlmostEqual(self.camera.forward.x, 1.0, places=9)
        self.assertAlmostEqual(self.camera.forward.y, 0.0, places=9)
        self.assertAlmostEqual(self.camera.forward.z, 0.0, places=9)

    def test_look_at_projects_target_to_center(self):
        self.camera.look_at((10, 0, 0))
        sx, sy, _ = self.camera.project((10, 0, 0))
        self.assertAlmostEqual(sx, 400.0, places=9)
        self.assertAlmostEqual(sy, 300.0, places=9)

    def test_look_at_same_point_raises(self):
        self.camera.position = (5, 5, 5)
        with self.assertRaises(ConfigurationError):
            self.camera.look_at((5, 5, 5))

    def test_look_at_up_and_down(self):
        self.camera.look_at((0, 10, 0))
        self.assertAlmostEqual(self.camera.forward.y, 1.0, places=9)
        self.camera.look_at((0, -10, 0))
        self.assertAlmostEqual(self.camera.forward.y, -1.0, places=9)

    def test_rotation_yaw_turns(self):
        self.camera.rotation = Quaternion.from_euler(90, 0, 0)
        self.assertAlmostEqual(self.camera.forward.x, 1.0, places=9)

    def test_world_to_camera(self):
        cam = self.camera.world_to_camera((0, 0, -5))
        self.assertEqual(cam, Vector3(0, 0, -5))
        self.assertEqual(self.camera.world_to_camera((3, 4, 0)), Vector3(3, 4, 0))


class TestCamera3DControl(unittest.TestCase):
    def test_position_controls(self):
        c = Camera3D()
        c.x = 1
        c.y = 2
        c.z = 3
        self.assertEqual(c.position, Vector3(1, 2, 3))
        c.move(1, 1, 1)
        self.assertEqual(c.position, Vector3(2, 3, 4))

    def test_update_validates_dt(self):
        c = Camera3D()
        c.update(0.016)
        with self.assertRaises(ConfigurationError):
            c.update(-1)
        with self.assertRaises(ConfigurationError):
            c.update("x")

    def test_enabled_flag(self):
        c = Camera3D()
        c.enabled = False
        self.assertFalse(c.enabled)


if __name__ == "__main__":
    unittest.main()
