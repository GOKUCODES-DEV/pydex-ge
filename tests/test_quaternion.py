"""Tests for the Part 3D Quaternion rotation type."""

import unittest

from pydex_ge import ConfigurationError, Quaternion, Vector3


class TestQuaternionConstruction(unittest.TestCase):
    def test_identity_default(self):
        q = Quaternion()
        self.assertEqual(q, Quaternion(1, 0, 0, 0))
        self.assertEqual(Quaternion.identity(), Quaternion(1, 0, 0, 0))

    def test_components_and_setters(self):
        q = Quaternion(1, 2, 3, 4)
        self.assertEqual((q.w, q.x, q.y, q.z), (1.0, 2.0, 3.0, 4.0))
        q.w = 5
        self.assertEqual(q.w, 5.0)

    def test_bool_rejected(self):
        with self.assertRaises(ConfigurationError):
            Quaternion(True, 0, 0, 0)

    def test_length(self):
        q = Quaternion(1, 2, 2, 4)
        self.assertAlmostEqual(q.length, 5.0)

    def test_normalized_zero_becomes_identity(self):
        self.assertEqual(Quaternion(0, 0, 0, 0).normalized(), Quaternion.identity())


class TestQuaternionRotation(unittest.TestCase):
    def test_rotate_identity_is_noop(self):
        self.assertEqual(Quaternion.identity().rotate_vector(Vector3(1, 2, 3)), Vector3(1, 2, 3))

    def test_rotate_x_90(self):
        q = Quaternion.from_axis_angle(Vector3(1, 0, 0), 90)
        r = q.rotate_vector(Vector3(0, 1, 0))
        self.assertAlmostEqual(r.x, 0.0)
        self.assertAlmostEqual(r.y, 0.0, places=9)
        self.assertAlmostEqual(r.z, 1.0, places=9)

    def test_rotate_y_90(self):
        q = Quaternion.from_euler(90, 0, 0)
        r = q.rotate_vector(Vector3(0, 0, 1))
        self.assertAlmostEqual(r.x, 1.0, places=9)
        self.assertAlmostEqual(r.y, 0.0, places=9)
        self.assertAlmostEqual(r.z, 0.0, places=9)

    def test_preserves_length(self):
        q = Quaternion.from_euler(30, 20, 10)
        v = Vector3(3, 4, 5)
        self.assertAlmostEqual(q.rotate_vector(v).length, v.length)

    def test_axis_angle_requires_nonzero_axis(self):
        with self.assertRaises(ConfigurationError):
            Quaternion.from_axis_angle(Vector3(0, 0, 0), 90)

    def test_axis_angle_accepts_tuple(self):
        q = Quaternion.from_axis_angle((0, 1, 0), 90)
        r = q.rotate_vector(Vector3(0, 0, 1))
        self.assertAlmostEqual(r.x, 1.0, places=9)

    def test_to_euler_roundtrip(self):
        for euler in [(0, 0, 0), (30, 20, 10), (-120, 45, 80), (90, 0, 0), (0, 0, 45)]:
            q = Quaternion.from_euler(*euler)
            back = q.to_euler()
            for got, want in zip(back, euler):
                self.assertAlmostEqual(got, want, places=6, msg=str(euler))


class TestQuaternionComposition(unittest.TestCase):
    def test_multiply_composes(self):
        # Applying roll about Z first, then yaw about Y: +Z stays +Z under
        # roll, then yaw turns it toward +X.
        roll = Quaternion.from_euler(0, 0, 90)
        yaw = Quaternion.from_euler(90, 0, 0)
        combined = yaw * roll  # apply roll first, then yaw
        r = combined.rotate_vector(Vector3(0, 0, 1))
        self.assertAlmostEqual(r.x, 1.0, places=9)
        self.assertAlmostEqual(r.y, 0.0, places=9)
        self.assertAlmostEqual(r.z, 0.0, places=9)

    def test_multiply_apply_yaw_then_roll(self):
        # q = roll * yaw applies yaw first, then roll: +Z -> +X -> +Y.
        roll = Quaternion.from_euler(0, 0, 90)
        yaw = Quaternion.from_euler(90, 0, 0)
        combined = roll * yaw
        r = combined.rotate_vector(Vector3(0, 0, 1))
        self.assertAlmostEqual(r.x, 0.0, places=9)
        self.assertAlmostEqual(r.y, 1.0, places=9)
        self.assertAlmostEqual(r.z, 0.0, places=9)

    def test_multiply_identity(self):
        q = Quaternion.from_euler(30, 10, 5)
        self.assertEqual(q * Quaternion.identity(), q)
        self.assertEqual(Quaternion.identity() * q, q)

    def test_multiply_type_error(self):
        with self.assertRaises(TypeError):
            Quaternion.identity() * 2

    def test_inverse_undoes_rotation(self):
        q = Quaternion.from_euler(40, -20, 15)
        v = Vector3(2, -3, 5)
        r = q.inverse().rotate_vector(q.rotate_vector(v))
        self.assertAlmostEqual(r.x, v.x, places=9)
        self.assertAlmostEqual(r.y, v.y, places=9)
        self.assertAlmostEqual(r.z, v.z, places=9)

    def test_conjugate_is_inverse_for_unit(self):
        q = Quaternion.from_euler(30, 20, 10).normalized()
        self.assertEqual(q.conjugate(), q.inverse())


class TestQuaternionProtocol(unittest.TestCase):
    def test_eq_tolerance(self):
        self.assertEqual(Quaternion(1, 0, 0, 0), Quaternion(1 + 1e-10, 0, 0, 0))
        self.assertNotEqual(Quaternion(1, 0, 0, 0), Quaternion(0, 1, 0, 0))

    def test_copy(self):
        q = Quaternion(1, 2, 3, 4)
        c = q.copy()
        self.assertEqual(c, q)
        self.assertIsNot(c, q)

    def test_repr(self):
        self.assertEqual(repr(Quaternion(1, 0, 0, 0)), "Quaternion(1.0, 0.0, 0.0, 0.0)")

    def test_hash(self):
        self.assertEqual(hash(Quaternion(1, 0, 0, 0)), hash(Quaternion(1, 0, 0, 0)))


if __name__ == "__main__":
    unittest.main()
