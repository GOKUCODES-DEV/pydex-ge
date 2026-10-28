"""Tests for the Part 3D Transform3D (position, quaternion rotation, scale, parents)."""

import unittest

from pydex_ge import ConfigurationError, Quaternion, Transform3D, Vector3


def assert_euler(testcase, transform, expected):
    euler = transform.rotation_euler
    for got, want in zip(euler, expected):
        testcase.assertAlmostEqual(got, want, places=6)


class TestTransform3DConstruction(unittest.TestCase):
    def test_defaults(self):
        t = Transform3D()
        self.assertEqual(t.position, Vector3(0, 0, 0))
        self.assertEqual(t.rotation, Quaternion.identity())
        self.assertEqual(t.scale, Vector3(1, 1, 1))
        self.assertEqual(t.origin, Vector3(0, 0, 0))
        self.assertIsNone(t.parent)
        self.assertEqual(t.children, ())

    def test_constructor_values(self):
        t = Transform3D(
            position=(1, 2, 3),
            rotation=Quaternion.from_euler(0, 45, 0),
            scale=(2, 1, 0.5),
            origin=(0.5, 0.5, 0.5),
        )
        self.assertEqual(t.position, Vector3(1, 2, 3))
        assert_euler(self, t, (0.0, 45.0, 0.0))
        self.assertEqual(t.scale, Vector3(2, 1, 0.5))
        self.assertEqual(t.origin, Vector3(0.5, 0.5, 0.5))

    def test_rotation_accepts_tuple(self):
        t = Transform3D(rotation=(1, 0, 0, 0))
        self.assertEqual(t.rotation, Quaternion.identity())

    def test_invalid_values(self):
        with self.assertRaises(ConfigurationError):
            Transform3D(position=(1, 2))
        with self.assertRaises(ConfigurationError):
            Transform3D(position="nope")
        with self.assertRaises(ConfigurationError):
            Transform3D(scale=0)
        with self.assertRaises(ConfigurationError):
            Transform3D(scale=(-1, 1, 1))
        with self.assertRaises(ConfigurationError):
            Transform3D(scale=True)
        with self.assertRaises(ConfigurationError):
            Transform3D(rotation="not-a-quaternion")


class TestTransform3DProperties(unittest.TestCase):
    def test_x_y_z_setters_and_move(self):
        t = Transform3D()
        t.x = 1
        t.y = 2
        t.z = 3
        self.assertEqual(t.position, Vector3(1, 2, 3))
        t.move(1, 1, 1)
        self.assertEqual(t.position, Vector3(2, 3, 4))

    def test_rotation_euler_property(self):
        t = Transform3D()
        t.rotation_euler = (0, 30, 0)
        assert_euler(self, t, (0.0, 30.0, 0.0))
        self.assertEqual(t.rotation, Quaternion.from_euler(0, 30, 0))

    def test_scale_axis_setters(self):
        t = Transform3D()
        t.scale_x = 2
        t.scale_y = 3
        t.scale_z = 4
        self.assertEqual(t.scale, Vector3(2, 3, 4))


class TestTransform3DParenting(unittest.TestCase):
    def test_world_position_follows_parent(self):
        parent = Transform3D(position=(5, 0, 0))
        child = Transform3D(position=(1, 2, 3), parent=parent)
        self.assertEqual(child.world_position, Vector3(6, 2, 3))
        self.assertEqual(child.local_position, Vector3(1, 2, 3))

    def test_world_rotation_combines(self):
        parent = Transform3D(rotation=Quaternion.from_euler(90, 0, 0))
        child = Transform3D(rotation=Quaternion.from_euler(45, 0, 0), parent=parent)
        self.assertAlmostEqual(child.world_rotation.to_euler()[0], 135.0, places=6)

    def test_world_scale_combines_per_axis(self):
        parent = Transform3D(scale=(2, 1, 1))
        child = Transform3D(scale=(1, 3, 1), parent=parent)
        self.assertEqual(child.world_scale, Vector3(2, 3, 1))

    def test_world_position_rotated_by_parent(self):
        parent = Transform3D(rotation=Quaternion.from_euler(90, 0, 0))
        child = Transform3D(position=(0, 0, 1), parent=parent)
        world = child.world_position
        self.assertAlmostEqual(world.x, 1.0, places=9)
        self.assertAlmostEqual(world.y, 0.0, places=9)
        self.assertAlmostEqual(world.z, 0.0, places=9)

    def test_add_remove_child(self):
        parent = Transform3D()
        child = Transform3D()
        self.assertIs(parent.add_child(child), child)
        self.assertIs(child.parent, parent)
        self.assertEqual(parent.children, (child,))
        self.assertTrue(parent.remove_child(child))
        self.assertIsNone(child.parent)
        self.assertFalse(parent.remove_child(child))


class TestTransform3DProtocol(unittest.TestCase):
    def test_copy(self):
        t = Transform3D(position=(1, 2, 3), rotation=Quaternion.from_euler(0, 30, 0))
        c = t.copy()
        self.assertEqual(c, t)
        self.assertIsNot(c, t)
        self.assertIsNone(c.parent)

    def test_eq(self):
        self.assertEqual(Transform3D(position=(1, 2, 3)), Transform3D(position=(1, 2, 3)))
        self.assertNotEqual(Transform3D(position=(1, 2, 3)), Transform3D(position=(1, 2, 4)))

    def test_repr(self):
        t = Transform3D(position=(1, 2, 3))
        self.assertIn("Transform3D", repr(t))
        self.assertIn("position=(1.0, 2.0, 3.0)", repr(t))


if __name__ == "__main__":
    unittest.main()
