"""Tests for the Part 12 Transform2D (position, rotation, scale, origin, parents)."""

import unittest

from pydex_ge import ConfigurationError, Transform2D, Vector2


class TestTransformConstruction(unittest.TestCase):
    def test_defaults(self):
        t = Transform2D()
        self.assertEqual(t.position, Vector2(0, 0))
        self.assertEqual(t.rotation, 0.0)
        self.assertEqual(t.scale, 1.0)
        self.assertEqual(t.origin, (0.0, 0.0))
        self.assertIsNone(t.parent)
        self.assertEqual(t.children, ())

    def test_constructor_values(self):
        t = Transform2D(position=(10, 20), rotation=45, scale=(2, 1), origin=(0.5, 0.5))
        self.assertEqual(t.position, Vector2(10, 20))
        self.assertEqual(t.rotation, 45.0)
        self.assertEqual(t.scale, (2.0, 1.0))
        self.assertEqual(t.origin, (0.5, 0.5))

    def test_constructor_vector2_position(self):
        t = Transform2D(position=Vector2(3, 4))
        self.assertEqual(t.position, Vector2(3, 4))

    def test_invalid_position(self):
        with self.assertRaises(ConfigurationError):
            Transform2D(position=(1, 2, 3))
        with self.assertRaises(ConfigurationError):
            Transform2D(position="nope")

    def test_invalid_scale(self):
        with self.assertRaises(ConfigurationError):
            Transform2D(scale=0)
        with self.assertRaises(ConfigurationError):
            Transform2D(scale=-1)
        with self.assertRaises(ConfigurationError):
            Transform2D(scale=(1, 2, 3))
        with self.assertRaises(ConfigurationError):
            Transform2D(scale=True)


class TestTransformProperties(unittest.TestCase):
    def test_x_y_setters(self):
        t = Transform2D()
        t.x = 5
        t.y = 7
        self.assertEqual(t.position, Vector2(5, 7))
        with self.assertRaises(ConfigurationError):
            t.x = "five"
        with self.assertRaises(ConfigurationError):
            t.y = True

    def test_position_setter(self):
        t = Transform2D()
        t.position = (9, 8)
        self.assertEqual((t.x, t.y), (9.0, 8.0))
        t.position = Vector2(1, 2)
        self.assertEqual((t.x, t.y), (1.0, 2.0))

    def test_move(self):
        t = Transform2D(position=(10, 10))
        t.move(5, -3)
        self.assertEqual(t.position, Vector2(15, 7))
        with self.assertRaises(ConfigurationError):
            t.move("a", 0)

    def test_rotation_setter(self):
        t = Transform2D()
        t.rotation = 90
        self.assertEqual(t.rotation, 90.0)
        with self.assertRaises(ConfigurationError):
            t.rotation = "wide"

    def test_scale_uniform_and_pair(self):
        t = Transform2D()
        t.scale = 2
        self.assertEqual(t.scale, 2.0)
        self.assertEqual(t.scale_x, 2.0)
        self.assertEqual(t.scale_y, 2.0)
        t.scale = (2, 1)
        self.assertEqual(t.scale, (2.0, 1.0))
        t.scale = Vector2(3, 3)
        self.assertEqual(t.scale, 3.0)
        with self.assertRaises(ConfigurationError):
            t.scale_x = 0
        with self.assertRaises(ConfigurationError):
            t.scale_y = -2

    def test_origin(self):
        t = Transform2D()
        t.origin = (0.5, 0.5)
        self.assertEqual(t.origin, (0.5, 0.5))
        with self.assertRaises(ConfigurationError):
            t.origin = (0.5,)

    def test_parent_validation(self):
        t = Transform2D()
        with self.assertRaises(ConfigurationError):
            t.parent = "root"


class TestTransformHierarchy(unittest.TestCase):
    def test_world_position_follows_parent(self):
        parent = Transform2D(position=(100, 50))
        child = Transform2D(position=(10, 20), parent=parent)
        self.assertEqual(child.world_position, Vector2(110, 70))
        parent.position = (200, 80)
        self.assertEqual(child.world_position, Vector2(210, 100))
        self.assertEqual(child.local_position, Vector2(10, 20))

    def test_world_position_applies_parent_rotation_and_scale(self):
        parent = Transform2D(position=(100, 100), rotation=90)
        child = Transform2D(position=(10, 0), parent=parent)
        world = child.world_position
        self.assertAlmostEqual(world.x, 100.0)
        self.assertAlmostEqual(world.y, 110.0)

        parent = Transform2D(position=(0, 0), scale=2)
        child = Transform2D(position=(10, 5), parent=parent)
        self.assertEqual(child.world_position, Vector2(20, 10))

        parent = Transform2D(position=(0, 0), scale=2, rotation=90)
        child = Transform2D(position=(10, 0), parent=parent)
        world = child.world_position
        self.assertAlmostEqual(world.x, 0.0, places=6)
        self.assertAlmostEqual(world.y, 20.0)

    def test_world_rotation_adds(self):
        parent = Transform2D(rotation=45)
        child = Transform2D(rotation=10, parent=parent)
        self.assertEqual(child.world_rotation, 55.0)
        parent.rotation = 90
        self.assertEqual(child.world_rotation, 100.0)

    def test_world_scale_multiplies_componentwise(self):
        parent = Transform2D(scale=(2, 3))
        child = Transform2D(scale=(1.5, 1), parent=parent)
        self.assertEqual(child.world_scale, 3.0)  # (3.0, 3.0) formats to 3.0
        parent.scale = (2, 3)
        child.scale = (1, 2)
        self.assertEqual(child.world_scale, (2.0, 6.0))
        parent.scale = 2
        child.scale = 2
        self.assertEqual(child.world_scale, 4.0)

    def test_add_child_and_remove_child(self):
        parent = Transform2D()
        child = Transform2D()
        self.assertIs(parent.add_child(child), child)
        self.assertIn(child, parent.children)
        self.assertIs(child.parent, parent)
        self.assertTrue(parent.remove_child(child))
        self.assertNotIn(child, parent.children)
        self.assertIsNone(child.parent)
        self.assertFalse(parent.remove_child(child))

    def test_add_child_validation(self):
        parent = Transform2D()
        with self.assertRaises(ConfigurationError):
            parent.add_child("nope")
        with self.assertRaises(ConfigurationError):
            parent.remove_child("nope")

    def test_reparenting_updates_parent_children(self):
        first = Transform2D()
        second = Transform2D()
        child = Transform2D()
        first.add_child(child)
        child.parent = second
        self.assertNotIn(child, first.children)
        self.assertIn(child, second.children)
        self.assertIs(child.parent, second)

    def test_equality_with_tolerance(self):
        self.assertEqual(
            Transform2D(position=(1, 2), rotation=3, scale=(2, 1)),
            Transform2D(position=(1, 2), rotation=3, scale=(2, 1)),
        )
        self.assertEqual(
            Transform2D(position=(1, 2)),
            Transform2D(position=(1, 2)),
        )
        self.assertNotEqual(
            Transform2D(position=(1, 2)),
            Transform2D(position=(1, 3)),
        )
        self.assertNotEqual(Transform2D(), "not a transform")

    def test_repr(self):
        text = repr(Transform2D(position=(1, 2)))
        self.assertIn("Transform2D", text)
        self.assertIn("position", text)


if __name__ == "__main__":
    unittest.main()
