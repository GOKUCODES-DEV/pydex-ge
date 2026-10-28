"""Tests for the Part 3D Vector3 math type."""

import unittest

from pydex_ge import ConfigurationError, Vector3


class TestVector3Construction(unittest.TestCase):
    def test_defaults(self):
        v = Vector3()
        self.assertEqual(v.x, 0.0)
        self.assertEqual(v.y, 0.0)
        self.assertEqual(v.z, 0.0)

    def test_single_value_sets_all(self):
        v = Vector3(5)
        self.assertEqual(v, Vector3(5, 5, 5))

    def test_tuple_unpacking(self):
        v = Vector3((1, 2, 3))
        self.assertEqual(v, Vector3(1, 2, 3))
        v2 = Vector3([4, 5, 6])
        self.assertEqual(v2, Vector3(4, 5, 6))

    def test_wrong_tuple_length(self):
        with self.assertRaises(ConfigurationError):
            Vector3((1, 2))
        with self.assertRaises(ConfigurationError):
            Vector3((1, 2, 3, 4))

    def test_bool_rejected(self):
        with self.assertRaises(ConfigurationError):
            Vector3(True, 2, 3)
        with self.assertRaises(ConfigurationError):
            Vector3(1, 2, "z")

    def test_ints_stored_as_floats(self):
        v = Vector3(1, 2, 3)
        self.assertIsInstance(v.x, float)
        self.assertEqual(v.x, 1.0)

    def test_setters(self):
        v = Vector3()
        v.x = 1
        v.y = 2
        v.z = 3
        self.assertEqual(v, Vector3(1, 2, 3))


class TestVector3Arithmetic(unittest.TestCase):
    def test_add_sub(self):
        self.assertEqual(Vector3(1, 2, 3) + Vector3(4, 5, 6), Vector3(5, 7, 9))
        self.assertEqual(Vector3(4, 5, 6) - Vector3(1, 2, 3), Vector3(3, 3, 3))

    def test_mul_scalar_and_vector(self):
        self.assertEqual(Vector3(1, 2, 3) * 2, Vector3(2, 4, 6))
        self.assertEqual(2 * Vector3(1, 2, 3), Vector3(2, 4, 6))
        self.assertEqual(Vector3(1, 2, 3) * Vector3(2, 3, 4), Vector3(2, 6, 12))

    def test_div(self):
        self.assertEqual(Vector3(2, 4, 6) / 2, Vector3(1, 2, 3))
        self.assertEqual(Vector3(2, 4, 6) / Vector3(2, 2, 2), Vector3(1, 2, 3))

    def test_neg(self):
        self.assertEqual(-Vector3(1, 2, 3), Vector3(-1, -2, -3))

    def test_type_errors(self):
        with self.assertRaises(TypeError):
            Vector3(1, 2, 3) + 5
        with self.assertRaises(TypeError):
            Vector3(1, 2, 3) * "x"
        with self.assertRaises(TypeError):
            Vector3(1, 2, 3) / "x"

    def test_zero_division(self):
        with self.assertRaises(ZeroDivisionError):
            Vector3(1, 2, 3) / 0
        with self.assertRaises(ZeroDivisionError):
            Vector3(1, 2, 3) / Vector3(1, 0, 1)

    def test_inplace(self):
        v = Vector3(1, 2, 3)
        v += Vector3(1, 1, 1)
        self.assertEqual(v, Vector3(2, 3, 4))
        v *= 2
        self.assertEqual(v, Vector3(4, 6, 8))


class TestVector3Geometry(unittest.TestCase):
    def test_length(self):
        self.assertAlmostEqual(Vector3(1, 2, 2).length, 3.0)
        self.assertEqual(Vector3(1, 2, 3).length_squared, 14.0)

    def test_normalized(self):
        n = Vector3(0, 3, 0).normalized()
        self.assertAlmostEqual(n.length, 1.0)
        self.assertEqual(Vector3(0, 0, 0).normalized(), Vector3(0, 0, 0))

    def test_dot(self):
        self.assertEqual(Vector3(1, 2, 3).dot(Vector3(4, 5, 6)), 32.0)

    def test_cross(self):
        self.assertEqual(Vector3(1, 0, 0).cross(Vector3(0, 1, 0)), Vector3(0, 0, 1))
        self.assertEqual(Vector3(0, 1, 0).cross(Vector3(1, 0, 0)), Vector3(0, 0, -1))

    def test_distance(self):
        self.assertAlmostEqual(Vector3(0, 0, 0).distance(Vector3(3, 4, 0)), 5.0)

    def test_angle_between(self):
        self.assertAlmostEqual(Vector3(1, 0, 0).angle_between(Vector3(0, 1, 0)), 90.0)
        self.assertEqual(Vector3(0, 0, 0).angle_between(Vector3(1, 0, 0)), 0.0)

    def test_clamp_length(self):
        v = Vector3(3, 0, 0).clamp_length(2)
        self.assertEqual(v, Vector3(2, 0, 0))
        self.assertEqual(Vector3(1, 0, 0).clamp_length(5), Vector3(1, 0, 0))

    def test_classmethods(self):
        self.assertEqual(Vector3.zero(), Vector3(0, 0, 0))
        self.assertEqual(Vector3.one(), Vector3(1, 1, 1))
        self.assertEqual(Vector3.right(), Vector3(1, 0, 0))
        self.assertEqual(Vector3.up(), Vector3(0, 1, 0))
        self.assertEqual(Vector3.forward(), Vector3(0, 0, 1))


class TestVector3Protocol(unittest.TestCase):
    def test_sequence(self):
        v = Vector3(1, 2, 3)
        self.assertEqual(len(v), 3)
        self.assertEqual(v[0], 1.0)
        self.assertEqual(list(v), [1.0, 2.0, 3.0])
        with self.assertRaises(IndexError):
            v[3]

    def test_bool(self):
        self.assertTrue(Vector3(1, 0, 0))
        self.assertFalse(Vector3(0, 0, 0))

    def test_eq_tolerance(self):
        self.assertEqual(Vector3(1.0, 2.0, 3.0), Vector3(1.0 + 1e-10, 2.0, 3.0))
        self.assertNotEqual(Vector3(1, 2, 3), Vector3(1, 2, 4))

    def test_copy(self):
        v = Vector3(1, 2, 3)
        c = v.copy()
        self.assertEqual(c, v)
        self.assertIsNot(c, v)

    def test_repr(self):
        self.assertEqual(repr(Vector3(1, 2, 3)), "Vector3(1.0, 2.0, 3.0)")

    def test_hash(self):
        self.assertEqual(hash(Vector3(1, 2, 3)), hash(Vector3(1, 2, 3)))


if __name__ == "__main__":
    unittest.main()
