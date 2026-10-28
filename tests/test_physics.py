"""Headless tests for Part 7: Vector2, Rect, and collision predicates.

These are pure-math tests: no backend, no window, no audio.  They cover
construction and validation, arithmetic (including in-place operators),
geometry helpers, zero-length/zero-size edge cases, floating-point
equality, and every collision predicate.
"""

import unittest

import pydex_ge
from pydex_ge.exceptions import ConfigurationError
from pydex_ge.physics import (
    Rect,
    Vector2,
    circle_rect_overlap,
    circles_overlap,
    point_in_circle,
    point_in_rect,
    rects_overlap,
)


class TestVector2Construction(unittest.TestCase):
    def test_default_is_origin(self):
        v = Vector2()
        self.assertEqual(v.x, 0.0)
        self.assertEqual(v.y, 0.0)

    def test_two_arguments(self):
        v = Vector2(3, 4)
        self.assertEqual(v.x, 3.0)
        self.assertEqual(v.y, 4.0)

    def test_floats_kept(self):
        v = Vector2(1.5, -2.25)
        self.assertEqual(v.x, 1.5)
        self.assertEqual(v.y, -2.25)

    def test_single_argument_sets_both(self):
        v = Vector2(5)
        self.assertEqual(v, Vector2(5, 5))

    def test_tuple_unpacked(self):
        v = Vector2((2, 7))
        self.assertEqual(v, Vector2(2, 7))

    def test_list_unpacked(self):
        v = Vector2([-1, 3])
        self.assertEqual(v, Vector2(-1, 3))

    def test_wrong_length_sequence(self):
        with self.assertRaises(ConfigurationError):
            Vector2((1, 2, 3))

    def test_bool_x_rejected(self):
        with self.assertRaises(ConfigurationError):
            Vector2(True, 2)

    def test_bool_y_rejected(self):
        with self.assertRaises(ConfigurationError):
            Vector2(1, False)

    def test_string_rejected(self):
        with self.assertRaises(ConfigurationError):
            Vector2("1", 2)

    def test_none_rejected(self):
        with self.assertRaises(ConfigurationError):
            Vector2(None, 2)

    def test_from_polar_right(self):
        v = Vector2.from_polar(1, 0)
        self.assertAlmostEqual(v.x, 1.0, places=9)
        self.assertAlmostEqual(v.y, 0.0, places=9)

    def test_from_polar_down(self):
        v = Vector2.from_polar(2, 90)
        self.assertAlmostEqual(v.x, 0.0, places=9)
        self.assertAlmostEqual(v.y, 2.0, places=9)

    def test_from_polar_negative_length(self):
        with self.assertRaises(ConfigurationError):
            Vector2.from_polar(-1, 0)

    def test_from_polar_bool_length(self):
        with self.assertRaises(ConfigurationError):
            Vector2.from_polar(True, 0)

    def test_zero_classmethod(self):
        self.assertEqual(Vector2.zero(), Vector2(0, 0))


class TestVector2Setters(unittest.TestCase):
    def test_set_x(self):
        v = Vector2(1, 2)
        v.x = 9
        self.assertEqual(v.x, 9.0)
        self.assertEqual(v.y, 2.0)

    def test_set_y(self):
        v = Vector2(1, 2)
        v.y = -4.5
        self.assertEqual(v.y, -4.5)

    def test_set_x_bool_rejected(self):
        v = Vector2(1, 2)
        with self.assertRaises(ConfigurationError):
            v.x = True

    def test_set_y_string_rejected(self):
        v = Vector2(1, 2)
        with self.assertRaises(ConfigurationError):
            v.y = "nope"


class TestVector2Arithmetic(unittest.TestCase):
    def test_add(self):
        self.assertEqual(Vector2(1, 2) + Vector2(3, 4), Vector2(4, 6))

    def test_sub(self):
        self.assertEqual(Vector2(5, 7) - Vector2(2, 3), Vector2(3, 4))

    def test_mul_scalar(self):
        self.assertEqual(Vector2(2, 3) * 4, Vector2(8, 12))

    def test_rmul_scalar(self):
        self.assertEqual(4 * Vector2(2, 3), Vector2(8, 12))

    def test_mul_float_scalar(self):
        self.assertEqual(Vector2(2, 3) * 0.5, Vector2(1.0, 1.5))

    def test_mul_vector(self):
        self.assertEqual(Vector2(2, 3) * Vector2(4, 5), Vector2(8, 15))

    def test_truediv_scalar(self):
        self.assertEqual(Vector2(4, 6) / 2, Vector2(2, 3))

    def test_truediv_float(self):
        self.assertEqual(Vector2(1, 2) / 0.5, Vector2(2, 4))

    def test_truediv_by_zero_scalar(self):
        with self.assertRaises(ZeroDivisionError):
            Vector2(1, 2) / 0

    def test_truediv_by_zero_vector(self):
        with self.assertRaises(ZeroDivisionError):
            Vector2(1, 2) / Vector2(0, 1)

    def test_neg(self):
        self.assertEqual(-Vector2(1, -2), Vector2(-1, 2))

    def test_add_wrong_type(self):
        with self.assertRaises(TypeError):
            Vector2(1, 2) + 5

    def test_mul_wrong_type(self):
        with self.assertRaises(TypeError):
            Vector2(1, 2) * "x"

    def test_mul_bool(self):
        with self.assertRaises(TypeError):
            Vector2(1, 2) * True


class TestVector2InPlace(unittest.TestCase):
    def test_iadd(self):
        v = Vector2(1, 2)
        v += Vector2(3, 4)
        self.assertEqual(v, Vector2(4, 6))

    def test_isub(self):
        v = Vector2(5, 7)
        v -= Vector2(2, 3)
        self.assertEqual(v, Vector2(3, 4))

    def test_imul(self):
        v = Vector2(2, 3)
        v *= 4
        self.assertEqual(v, Vector2(8, 12))

    def test_itruediv(self):
        v = Vector2(4, 6)
        v /= 2
        self.assertEqual(v, Vector2(2, 3))

    def test_iadd_returns_self(self):
        v = Vector2(1, 2)
        result = v.__iadd__(Vector2(1, 1))
        self.assertIs(result, v)

    def test_imul_by_zero_ok(self):
        v = Vector2(4, 6)
        v *= 0
        self.assertEqual(v, Vector2(0, 0))

    def test_itruediv_by_zero(self):
        v = Vector2(1, 2)
        with self.assertRaises(ZeroDivisionError):
            v /= 0


class TestVector2Geometry(unittest.TestCase):
    def test_length(self):
        self.assertAlmostEqual(Vector2(3, 4).length, 5.0, places=9)

    def test_length_squared(self):
        self.assertEqual(Vector2(3, 4).length_squared, 25.0)

    def test_zero_length(self):
        self.assertEqual(Vector2(0, 0).length, 0.0)

    def test_normalized(self):
        n = Vector2(3, 4).normalized()
        self.assertAlmostEqual(n.length, 1.0, places=9)
        self.assertAlmostEqual(n.x, 0.6, places=9)
        self.assertAlmostEqual(n.y, 0.8, places=9)

    def test_normalized_zero_is_zero(self):
        self.assertEqual(Vector2(0, 0).normalized(), Vector2(0, 0))

    def test_dot(self):
        self.assertEqual(Vector2(1, 2).dot(Vector2(3, 4)), 11.0)

    def test_dot_perpendicular_is_zero(self):
        self.assertAlmostEqual(Vector2(1, 0).dot(Vector2(0, 1)), 0.0, places=9)

    def test_dot_wrong_type(self):
        with self.assertRaises(TypeError):
            Vector2(1, 2).dot(5)

    def test_cross(self):
        self.assertEqual(Vector2(1, 0).cross(Vector2(0, 1)), 1.0)
        self.assertEqual(Vector2(0, 1).cross(Vector2(1, 0)), -1.0)

    def test_distance(self):
        self.assertAlmostEqual(Vector2(0, 0).distance(Vector2(3, 4)), 5.0, places=9)

    def test_distance_same_point(self):
        self.assertEqual(Vector2(1, 1).distance(Vector2(1, 1)), 0.0)

    def test_rotate_90(self):
        v = Vector2(1, 0).rotate(90)
        self.assertAlmostEqual(v.x, 0.0, places=9)
        self.assertAlmostEqual(v.y, 1.0, places=9)

    def test_rotate_matches_from_polar(self):
        self.assertEqual(Vector2(1, 0).rotate(90), Vector2.from_polar(1, 90))

    def test_rotate_180(self):
        v = Vector2(2, 3).rotate(180)
        self.assertAlmostEqual(v.x, -2.0, places=9)
        self.assertAlmostEqual(v.y, -3.0, places=9)

    def test_rotate_0_unchanged(self):
        v = Vector2(2, 3).rotate(0)
        self.assertAlmostEqual(v.x, 2.0, places=9)
        self.assertAlmostEqual(v.y, 3.0, places=9)

    def test_rotate_preserves_length(self):
        v = Vector2(3, 4).rotate(37)
        self.assertAlmostEqual(v.length, 5.0, places=9)

    def test_perpendicular(self):
        self.assertEqual(Vector2(1, 2).perpendicular(), Vector2(-2, 1))

    def test_perpendicular_dot_zero(self):
        v = Vector2(1, 2)
        self.assertAlmostEqual(v.dot(v.perpendicular()), 0.0, places=9)

    def test_clamp_length_noop(self):
        v = Vector2(3, 4)
        self.assertEqual(v.clamp_length(10), v)

    def test_clamp_length_reduces(self):
        clamped = Vector2(6, 8).clamp_length(5)
        self.assertAlmostEqual(clamped.length, 5.0, places=9)
        self.assertAlmostEqual(clamped.x, 3.0, places=9)
        self.assertAlmostEqual(clamped.y, 4.0, places=9)

    def test_clamp_length_zero_vector(self):
        self.assertEqual(Vector2(0, 0).clamp_length(5), Vector2(0, 0))

    def test_clamp_length_negative_max(self):
        with self.assertRaises(ConfigurationError):
            Vector2(1, 1).clamp_length(-1)

    def test_copy_is_independent(self):
        v = Vector2(1, 2)
        c = v.copy()
        c.x = 9
        self.assertEqual(v.x, 1.0)


class TestVector2Protocol(unittest.TestCase):
    def test_equality_tolerant(self):
        self.assertEqual(Vector2(1.0, 2.0), Vector2(1.0 + 1e-10, 2.0))

    def test_inequality(self):
        self.assertNotEqual(Vector2(1, 2), Vector2(2, 1))

    def test_not_equal_to_other_type(self):
        self.assertNotEqual(Vector2(1, 2), (1, 2))

    def test_tuple_conversion(self):
        self.assertEqual(tuple(Vector2(1.5, 2.5)), (1.5, 2.5))

    def test_len(self):
        self.assertEqual(len(Vector2(1, 2)), 2)

    def test_indexing(self):
        v = Vector2(4, 9)
        self.assertEqual(v[0], 4.0)
        self.assertEqual(v[1], 9.0)

    def test_indexing_out_of_range(self):
        with self.assertRaises(IndexError):
            Vector2(1, 2)[2]

    def test_iter_unpacks(self):
        x, y = Vector2(3, 8)
        self.assertEqual((x, y), (3.0, 8.0))

    def test_bool_truthy(self):
        self.assertTrue(Vector2(1, 0))

    def test_bool_falsy(self):
        self.assertFalse(Vector2(0, 0))

    def test_repr(self):
        self.assertEqual(repr(Vector2(1, 2)), "Vector2(1.0, 2.0)")


class TestRectConstruction(unittest.TestCase):
    def test_default(self):
        r = Rect()
        self.assertEqual((r.x, r.y, r.width, r.height), (0.0, 0.0, 0.0, 0.0))

    def test_full_args(self):
        r = Rect(1, 2, 30, 40)
        self.assertEqual((r.x, r.y, r.width, r.height), (1.0, 2.0, 30.0, 40.0))

    def test_float_support(self):
        r = Rect(0.5, 1.5, 10.25, 20.75)
        self.assertEqual((r.x, r.y, r.width, r.height), (0.5, 1.5, 10.25, 20.75))

    def test_position_keyword(self):
        r = Rect(position=(3, 4), width=10, height=20)
        self.assertEqual((r.x, r.y, r.width, r.height), (3.0, 4.0, 10.0, 20.0))

    def test_position_vector(self):
        r = Rect(position=Vector2(3, 4), width=10, height=20)
        self.assertEqual((r.x, r.y), (3.0, 4.0))

    def test_size_keyword(self):
        r = Rect(1, 2, size=(5, 6))
        self.assertEqual((r.width, r.height), (5.0, 6.0))

    def test_size_vector(self):
        r = Rect(1, 2, size=Vector2(5, 6))
        self.assertEqual((r.width, r.height), (5.0, 6.0))

    def test_zero_size_allowed(self):
        r = Rect(1, 2, 0, 0)
        self.assertEqual((r.width, r.height), (0.0, 0.0))

    def test_negative_width_rejected(self):
        with self.assertRaises(ConfigurationError):
            Rect(0, 0, -1, 5)

    def test_negative_height_rejected(self):
        with self.assertRaises(ConfigurationError):
            Rect(0, 0, 5, -1)

    def test_bool_width_rejected(self):
        with self.assertRaises(ConfigurationError):
            Rect(0, 0, True, 5)

    def test_string_position_rejected(self):
        with self.assertRaises(ConfigurationError):
            Rect(position="bad", width=1, height=1)

    def test_negative_x_allowed(self):
        r = Rect(-5, -3, 10, 10)
        self.assertEqual((r.x, r.y), (-5.0, -3.0))

    def test_bad_position_length(self):
        with self.assertRaises(ConfigurationError):
            Rect(position=(1, 2, 3), width=1, height=1)


class TestRectGeometry(unittest.TestCase):
    def setUp(self):
        self.rect = Rect(10, 20, 100, 50)

    def test_edges(self):
        self.assertEqual(self.rect.left, 10.0)
        self.assertEqual(self.rect.right, 110.0)
        self.assertEqual(self.rect.top, 20.0)
        self.assertEqual(self.rect.bottom, 70.0)

    def test_center(self):
        c = self.rect.center
        self.assertEqual(c, Vector2(60, 45))

    def test_corners(self):
        self.assertEqual(self.rect.top_left, Vector2(10, 20))
        self.assertEqual(self.rect.top_right, Vector2(110, 20))
        self.assertEqual(self.rect.bottom_left, Vector2(10, 70))
        self.assertEqual(self.rect.bottom_right, Vector2(110, 70))

    def test_size(self):
        self.assertEqual(self.rect.size, Vector2(100, 50))

    def test_zero_size_center(self):
        r = Rect(5, 5, 0, 0)
        self.assertEqual(r.center, Vector2(5, 5))

    def test_contains_point_inside(self):
        self.assertTrue(self.rect.contains_point((60, 45)))

    def test_contains_point_on_edge(self):
        self.assertTrue(self.rect.contains_point((10, 30)))

    def test_contains_point_on_corner(self):
        self.assertTrue(self.rect.contains_point((110, 70)))

    def test_contains_point_outside(self):
        self.assertFalse(self.rect.contains_point((120, 45)))

    def test_contains_point_vector(self):
        self.assertTrue(self.rect.contains_point(Vector2(60, 45)))

    def test_contains_point_bool_in_tuple_rejected(self):
        with self.assertRaises(ConfigurationError):
            self.rect.contains_point((True, 45))


class TestRectRelations(unittest.TestCase):
    def test_overlap_interior(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(5, 5, 10, 10)
        self.assertTrue(a.overlaps(b))

    def test_overlap_touching_edges(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(10, 0, 10, 10)
        self.assertTrue(a.overlaps(b))

    def test_overlap_touching_corner(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(10, 10, 5, 5)
        self.assertTrue(a.overlaps(b))

    def test_no_overlap(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(20, 20, 5, 5)
        self.assertFalse(a.overlaps(b))

    def test_contains(self):
        self.assertTrue(Rect(0, 0, 100, 100).contains(Rect(10, 10, 20, 20)))

    def test_contains_touching(self):
        self.assertTrue(Rect(0, 0, 100, 100).contains(Rect(0, 0, 100, 100)))

    def test_not_contains(self):
        self.assertFalse(Rect(0, 0, 10, 10).contains(Rect(5, 5, 10, 10)))

    def test_contains_self(self):
        r = Rect(1, 1, 5, 5)
        self.assertTrue(r.contains(r))

    def test_intersection_overlap(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(5, 5, 10, 10)
        self.assertEqual(a.intersection(b), Rect(5, 5, 5, 5))

    def test_intersection_contained(self):
        a = Rect(0, 0, 100, 100)
        b = Rect(10, 10, 20, 20)
        self.assertEqual(a.intersection(b), b)

    def test_intersection_none(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(20, 20, 5, 5)
        self.assertIsNone(a.intersection(b))

    def test_intersection_touching_edges_zero_area(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(10, 0, 5, 5)
        result = a.intersection(b)
        self.assertIsNotNone(result)
        self.assertEqual(result.width, 0.0)

    def test_union(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(20, 30, 5, 5)
        self.assertEqual(a.union(b), Rect(0, 0, 25, 35))

    def test_union_overlapping(self):
        a = Rect(0, 0, 10, 10)
        b = Rect(5, 5, 10, 10)
        self.assertEqual(a.union(b), Rect(0, 0, 15, 15))


class TestRectTransform(unittest.TestCase):
    def test_inflate_positive(self):
        r = Rect(10, 10, 10, 10)
        self.assertEqual(r.inflate(2, 3), Rect(8, 7, 14, 16))

    def test_inflate_negative(self):
        r = Rect(0, 0, 10, 10)
        self.assertEqual(r.inflate(-2, -2), Rect(2, 2, 6, 6))

    def test_inflate_below_zero_size(self):
        with self.assertRaises(ConfigurationError):
            Rect(0, 0, 4, 4).inflate(-3, -3)

    def test_inflate_does_not_mutate(self):
        r = Rect(0, 0, 10, 10)
        r.inflate(2, 2)
        self.assertEqual(r, Rect(0, 0, 10, 10))

    def test_moved(self):
        r = Rect(10, 10, 5, 5)
        self.assertEqual(r.moved(3, -2), Rect(13, 8, 5, 5))

    def test_move_in_place(self):
        r = Rect(10, 10, 5, 5)
        r.move(3, -2)
        self.assertEqual(r, Rect(13, 8, 5, 5))

    def test_copy_is_independent(self):
        r = Rect(1, 2, 3, 4)
        c = r.copy()
        c.x = 99
        self.assertEqual(r.x, 1.0)


class TestRectProtocol(unittest.TestCase):
    def test_equality(self):
        self.assertEqual(Rect(1, 2, 3, 4), Rect(1.0, 2.0, 3.0, 4.0))

    def test_equality_tolerant(self):
        self.assertEqual(Rect(1, 2, 3, 4), Rect(1 + 1e-10, 2, 3, 4))

    def test_inequality(self):
        self.assertNotEqual(Rect(1, 2, 3, 4), Rect(1, 2, 3, 5))

    def test_repr(self):
        self.assertEqual(repr(Rect(1, 2, 3, 4)), "Rect(1.0, 2.0, 3.0, 4.0)")


class TestCollision(unittest.TestCase):
    def test_point_in_rect_inside(self):
        self.assertTrue(point_in_rect((5, 5), Rect(0, 0, 10, 10)))

    def test_point_in_rect_edge(self):
        self.assertTrue(point_in_rect((0, 5), Rect(0, 0, 10, 10)))

    def test_point_in_rect_outside(self):
        self.assertFalse(point_in_rect((15, 5), Rect(0, 0, 10, 10)))

    def test_point_in_rect_bad_rect(self):
        with self.assertRaises(ConfigurationError):
            point_in_rect((1, 1), (0, 0, 5, 5))

    def test_rects_overlap(self):
        self.assertTrue(rects_overlap(Rect(0, 0, 10, 10), Rect(5, 5, 10, 10)))

    def test_rects_overlap_touching(self):
        self.assertTrue(rects_overlap(Rect(0, 0, 10, 10), Rect(10, 0, 5, 5)))

    def test_rects_no_overlap(self):
        self.assertFalse(rects_overlap(Rect(0, 0, 10, 10), Rect(20, 20, 5, 5)))

    def test_rects_overlap_wrong_type(self):
        with self.assertRaises(ConfigurationError):
            rects_overlap(Rect(0, 0, 1, 1), (0, 0, 5, 5))

    def test_circles_overlap(self):
        self.assertTrue(circles_overlap((0, 0), 5, (3, 4), 5))

    def test_circles_overlap_touching(self):
        self.assertTrue(circles_overlap((0, 0), 5, (10, 0), 5))

    def test_circles_no_overlap(self):
        self.assertFalse(circles_overlap((0, 0), 5, (20, 0), 5))

    def test_circles_concentric(self):
        self.assertTrue(circles_overlap((0, 0), 3, (0, 0), 3))

    def test_circles_zero_radius_touching_center(self):
        self.assertTrue(circles_overlap((1, 1), 0, (1, 1), 0))

    def test_circles_negative_radius(self):
        with self.assertRaises(ConfigurationError):
            circles_overlap((0, 0), -1, (5, 5), 1)

    def test_circles_bool_radius(self):
        with self.assertRaises(ConfigurationError):
            circles_overlap((0, 0), True, (5, 5), 1)

    def test_point_in_circle_inside(self):
        self.assertTrue(point_in_circle((1, 1), (0, 0), 2))

    def test_point_in_circle_on_edge(self):
        self.assertTrue(point_in_circle((2, 0), (0, 0), 2))

    def test_point_in_circle_outside(self):
        self.assertFalse(point_in_circle((5, 0), (0, 0), 2))

    def test_point_in_circle_negative_radius(self):
        with self.assertRaises(ConfigurationError):
            point_in_circle((1, 1), (0, 0), -1)

    def test_circle_rect_overlap_inside(self):
        self.assertTrue(circle_rect_overlap((5, 5), 3, Rect(0, 0, 10, 10)))

    def test_circle_rect_overlap_near_edge(self):
        self.assertTrue(circle_rect_overlap((-2, 5), 3, Rect(0, 0, 10, 10)))

    def test_circle_rect_overlap_corner(self):
        self.assertTrue(circle_rect_overlap((-1, -1), 2, Rect(0, 0, 10, 10)))

    def test_circle_rect_no_overlap(self):
        self.assertFalse(circle_rect_overlap((-20, -20), 3, Rect(0, 0, 10, 10)))

    def test_circle_rect_touching_edge(self):
        self.assertTrue(circle_rect_overlap((-3, 5), 3, Rect(0, 0, 10, 10)))

    def test_circle_rect_negative_radius(self):
        with self.assertRaises(ConfigurationError):
            circle_rect_overlap((0, 0), -2, Rect(0, 0, 5, 5))

    def test_circle_rect_bad_rect(self):
        with self.assertRaises(ConfigurationError):
            circle_rect_overlap((0, 0), 2, (0, 0, 5, 5))


class TestPublicExports(unittest.TestCase):
    def test_top_level_exports(self):
        self.assertIs(pydex_ge.Vector2, Vector2)
        self.assertIs(pydex_ge.Rect, Rect)

    def test_physics_helpers_exported(self):
        import pydex_ge.physics as physics

        for name in ("point_in_rect", "rects_overlap", "circles_overlap",
                     "point_in_circle", "circle_rect_overlap"):
            self.assertTrue(callable(getattr(physics, name)))


if __name__ == "__main__":
    unittest.main()
