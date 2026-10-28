"""Headless tests for Part 7.5: Body, World, gravity, and static collision.

Pure-math tests: no backend, no window, no audio.  They cover construction
and validation, integration (update), force/impulse, gravity application,
and static-rectangle collision resolution.
"""

import unittest

import pydex_ge
from pydex_ge.exceptions import ConfigurationError
from pydex_ge.physics import Body, Rect, Vector2, World


class TestBodyConstruction(unittest.TestCase):
    def test_defaults(self):
        body = Body()
        self.assertEqual(body.position, Vector2(0, 0))
        self.assertEqual(body.velocity, Vector2(0, 0))
        self.assertEqual(body.acceleration, Vector2(0, 0))
        self.assertEqual(body.mass, 1.0)
        self.assertEqual(body.size, Vector2(1, 1))

    def test_full_args(self):
        body = Body(
            position=(10, 20),
            size=(30, 40),
            velocity=(1, 2),
            acceleration=(3, 4),
            mass=2.0,
        )
        self.assertEqual(body.position, Vector2(10, 20))
        self.assertEqual(body.size, Vector2(30, 40))
        self.assertEqual(body.velocity, Vector2(1, 2))
        self.assertEqual(body.acceleration, Vector2(3, 4))
        self.assertEqual(body.mass, 2.0)

    def test_vectors_accepted(self):
        body = Body(position=Vector2(1, 2), size=Vector2(3, 4))
        self.assertEqual(body.position, Vector2(1, 2))
        self.assertEqual(body.size, Vector2(3, 4))

    def test_zero_size_allowed(self):
        body = Body(size=(0, 0))
        self.assertEqual(body.size, Vector2(0, 0))

    def test_negative_size_rejected(self):
        with self.assertRaises(ConfigurationError):
            Body(size=(-1, 5))
        with self.assertRaises(ConfigurationError):
            Body(size=(5, -1))

    def test_bool_size_rejected(self):
        with self.assertRaises(ConfigurationError):
            Body(size=(True, 5))

    def test_zero_mass_rejected(self):
        with self.assertRaises(ConfigurationError):
            Body(mass=0)

    def test_negative_mass_rejected(self):
        with self.assertRaises(ConfigurationError):
            Body(mass=-1)

    def test_bool_mass_rejected(self):
        with self.assertRaises(ConfigurationError):
            Body(mass=True)

    def test_string_mass_rejected(self):
        with self.assertRaises(ConfigurationError):
            Body(mass="heavy")

    def test_bad_position_rejected(self):
        with self.assertRaises(ConfigurationError):
            Body(position="bad")

    def test_rect_property(self):
        body = Body(position=(10, 20), size=(30, 40))
        self.assertEqual(body.rect, Rect(10, 20, 30, 40))

    def test_copy_is_independent(self):
        body = Body(position=(1, 2), size=(3, 4), velocity=(5, 6))
        clone = body.copy()
        clone.position = (99, 99)
        clone.velocity = (0, 0)
        self.assertEqual(body.position, Vector2(1, 2))
        self.assertEqual(body.velocity, Vector2(5, 6))


class TestBodySetters(unittest.TestCase):
    def setUp(self):
        self.body = Body()

    def test_set_position(self):
        self.body.position = (5, 6)
        self.assertEqual(self.body.position, Vector2(5, 6))

    def test_set_position_vector(self):
        self.body.position = Vector2(7, 8)
        self.assertEqual(self.body.position, Vector2(7, 8))

    def test_set_position_bool_rejected(self):
        with self.assertRaises(ConfigurationError):
            self.body.position = (True, 2)

    def test_set_velocity(self):
        self.body.velocity = (1, 2)
        self.assertEqual(self.body.velocity, Vector2(1, 2))

    def test_set_acceleration(self):
        self.body.acceleration = (3, 4)
        self.assertEqual(self.body.acceleration, Vector2(3, 4))

    def test_set_mass(self):
        self.body.mass = 5
        self.assertEqual(self.body.mass, 5.0)

    def test_set_mass_negative(self):
        with self.assertRaises(ConfigurationError):
            self.body.mass = -1

    def test_set_width_height(self):
        self.body.width = 20
        self.body.height = 30
        self.assertEqual(self.body.size, Vector2(20, 30))

    def test_set_width_negative(self):
        with self.assertRaises(ConfigurationError):
            self.body.width = -1


class TestBodyIntegration(unittest.TestCase):
    def test_update_moves_by_velocity(self):
        body = Body(position=(0, 0), velocity=(10, 0))
        body.update(0.5)
        self.assertEqual(body.position, Vector2(5, 0))

    def test_update_accelerates_velocity(self):
        body = Body(velocity=(0, 0), acceleration=(0, 10))
        body.update(1.0)
        self.assertEqual(body.velocity, Vector2(0, 10))
        self.assertEqual(body.position, Vector2(0, 10))

    def test_semi_implicit_euler(self):
        # velocity updated first: position gains new velocity * dt.
        body = Body(velocity=(0, 1), acceleration=(0, 1))
        body.update(1.0)
        self.assertEqual(body.position, Vector2(0, 2))

    def test_update_repeated(self):
        body = Body(velocity=(0, 0), acceleration=(0, 10))
        for _ in range(3):
            body.update(1.0)
        # v: 10, 20, 30 ; pos: 10, 30, 60
        self.assertEqual(body.velocity, Vector2(0, 30))
        self.assertEqual(body.position, Vector2(0, 60))

    def test_update_negative_dt_rejected(self):
        body = Body()
        with self.assertRaises(ConfigurationError):
            body.update(-1)

    def test_update_bool_dt_rejected(self):
        body = Body()
        with self.assertRaises(ConfigurationError):
            body.update(True)

    def test_update_zero_dt_noop(self):
        body = Body(velocity=(5, 5))
        body.update(0)
        self.assertEqual(body.position, Vector2(0, 0))


class TestBodyForces(unittest.TestCase):
    def test_apply_force_scales_by_mass(self):
        body = Body(mass=2.0)
        body.apply_force((0, 10))
        # acceleration += force / mass = (0, 5)
        body.update(1.0)
        self.assertEqual(body.velocity, Vector2(0, 5))

    def test_apply_force_multiple_times(self):
        body = Body()
        body.apply_force((1, 0))
        body.apply_force((1, 0))
        body.update(1.0)
        self.assertEqual(body.velocity, Vector2(2, 0))

    def test_apply_impulse_changes_velocity(self):
        body = Body()
        body.apply_impulse((0, -100))
        self.assertEqual(body.velocity, Vector2(0, -100))

    def test_apply_force_bad_type(self):
        body = Body()
        with self.assertRaises(ConfigurationError):
            body.apply_force("push")


class TestBodyCollision(unittest.TestCase):
    def test_collides_with_overlap(self):
        body = Body(position=(0, 0), size=(10, 10))
        self.assertTrue(body.collides_with(Rect(5, 5, 10, 10)))

    def test_collides_with_touching(self):
        body = Body(position=(0, 0), size=(10, 10))
        self.assertTrue(body.collides_with(Rect(10, 0, 10, 10)))

    def test_collides_with_no_overlap(self):
        body = Body(position=(0, 0), size=(10, 10))
        self.assertFalse(body.collides_with(Rect(20, 20, 10, 10)))

    def test_collides_with_bad_type(self):
        body = Body()
        with self.assertRaises(ConfigurationError):
            body.collides_with((0, 0, 5, 5))

    def test_collide_static_floor(self):
        body = Body(position=(0, 95), size=(10, 10), velocity=(0, 50))
        floor = Rect(0, 100, 200, 10)
        result = body.collide_static(floor)
        self.assertTrue(result)
        self.assertEqual(body.position.y, 90.0)
        self.assertEqual(body.velocity.y, 0.0)

    def test_collide_static_no_overlap(self):
        body = Body(position=(0, 0), size=(10, 10), velocity=(0, 50))
        floor = Rect(0, 200, 200, 10)
        result = body.collide_static(floor)
        self.assertFalse(result)
        self.assertEqual(body.velocity.y, 50.0)

    def test_collide_static_touching_no_penetration(self):
        # Just touching (no penetration) is not a resolved collision; the
        # body keeps its velocity until it actually moves into the surface.
        body = Body(position=(0, 90), size=(10, 10), velocity=(0, 50))
        floor = Rect(0, 100, 200, 10)
        result = body.collide_static(floor)
        self.assertFalse(result)
        self.assertEqual(body.velocity.y, 50.0)

    def test_collide_static_hits_ceiling(self):
        body = Body(position=(0, 2), size=(10, 10), velocity=(0, -50))
        ceiling = Rect(0, 0, 200, 5)
        result = body.collide_static(ceiling)
        self.assertTrue(result)
        self.assertEqual(body.position.y, 5.0)
        self.assertEqual(body.velocity.y, 0.0)

    def test_collide_static_hits_left_wall(self):
        body = Body(position=(0, 0), size=(10, 10), velocity=(-50, 0))
        wall = Rect(0, 0, 5, 200)
        result = body.collide_static(wall)
        self.assertTrue(result)
        self.assertEqual(body.position.x, 5.0)
        self.assertEqual(body.velocity.x, 0.0)

    def test_collide_static_deep_floor_resolves_on_top(self):
        # A falling body that has sunk far into a floor must be ejected on
        # top (velocity-aware), not dumped out the shallow side below it.
        body = Body(position=(0, 8), size=(10, 10), velocity=(0, 100))
        floor = Rect(0, 10, 100, 5)
        result = body.collide_static(floor)
        self.assertTrue(result)
        self.assertEqual(body.position.y, 0.0)
        self.assertEqual(body.velocity.y, 0.0)

    def test_collide_static_deep_ceiling_resolves_below(self):
        # A body moving up deep into a ceiling is ejected on the bottom.
        body = Body(position=(0, 2), size=(10, 10), velocity=(0, -100))
        ceiling = Rect(0, 6, 100, 5)
        result = body.collide_static(ceiling)
        self.assertTrue(result)
        self.assertEqual(body.position.y, 11.0)
        self.assertEqual(body.velocity.y, 0.0)

    def test_collide_static_stationary_deep_overlap_uses_least_penetration(self):
        # No velocity: fall back to the shallowest exit side.
        body = Body(position=(0, 8), size=(10, 10), velocity=(0, 0))
        floor = Rect(0, 10, 100, 5)
        result = body.collide_static(floor)
        self.assertTrue(result)
        # overlap_bottom (7) is shallower than overlap_top (8): exit below.
        self.assertEqual(body.position.y, 15.0)
        self.assertEqual(body.velocity.y, 0.0)


class TestWorld(unittest.TestCase):
    def test_gravity_accumulates(self):
        world = World(gravity=(0, 500))
        body = Body(size=(10, 10))
        world.add_body(body)
        world.update(0.1)
        self.assertEqual(body.velocity, Vector2(0, 50))
        world.update(0.1)
        self.assertEqual(body.velocity, Vector2(0, 100))

    def test_gravity_moves_body_down(self):
        world = World(gravity=(0, 100))
        body = Body(position=(0, 0), size=(10, 10))
        world.add_body(body)
        world.update(1.0)
        self.assertEqual(body.position, Vector2(0, 100))

    def test_zero_gravity_no_motion(self):
        world = World(gravity=(0, 0))
        body = Body(position=(5, 5), size=(10, 10))
        world.add_body(body)
        world.update(1.0)
        self.assertEqual(body.position, Vector2(5, 5))

    def test_add_remove_clear_len(self):
        world = World()
        body = Body()
        self.assertEqual(len(world), 0)
        world.add_body(body)
        self.assertEqual(len(world), 1)
        world.remove_body(body)
        self.assertEqual(len(world), 0)
        world.add_body(body)
        world.clear()
        self.assertEqual(len(world), 0)

    def test_add_body_returns_body(self):
        world = World()
        body = Body()
        self.assertIs(world.add_body(body), body)

    def test_add_body_duplicate_noop(self):
        world = World()
        body = Body()
        world.add_body(body)
        world.add_body(body)
        self.assertEqual(len(world), 1)

    def test_add_body_bad_type(self):
        world = World()
        with self.assertRaises(ConfigurationError):
            world.add_body("not a body")

    def test_iteration(self):
        world = World()
        a = Body(position=(0, 0))
        b = Body(position=(10, 10))
        world.add_body(a)
        world.add_body(b)
        self.assertEqual(list(world), [a, b])

    def test_static_rects_from_constructor(self):
        world = World(static_rects=(Rect(0, 100, 200, 10),))
        body = Body(position=(0, 90), size=(10, 10))
        world.add_body(body)
        world.update(0.1)
        self.assertLessEqual(body.position.y, 90.0)
        self.assertEqual(body.velocity.y, 0.0)

    def test_static_rects_bad_type(self):
        with self.assertRaises(ConfigurationError):
            World(static_rects=((0, 0, 5, 5),))

    def test_negative_dt_rejected(self):
        world = World()
        world.add_body(Body())
        with self.assertRaises(ConfigurationError):
            world.update(-0.1)

    def test_bool_dt_rejected(self):
        world = World()
        world.add_body(Body())
        with self.assertRaises(ConfigurationError):
            world.update(True)


class TestWorldFallingAndLanding(unittest.TestCase):
    def test_body_falls_and_rests_on_floor(self):
        world = World(gravity=(0, 500), static_rects=(Rect(0, 480, 640, 20),))
        body = Body(position=(320, 0), size=(40, 40))
        world.add_body(body)
        for _ in range(200):
            world.update(0.016)
        # Body should rest on the floor: its bottom at y=480.
        self.assertAlmostEqual(body.rect.bottom, 480.0, places=3)
        self.assertEqual(body.velocity.y, 0.0)

    def test_embedded_body_resolves_upward(self):
        # A body already overlapping a floor (bottom below the floor top)
        # gets pushed out on top, not through the sides.
        world = World(gravity=(0, 0), static_rects=(Rect(0, 480, 640, 20),))
        body = Body(position=(320, 460), size=(40, 40), velocity=(0, 0))
        world.add_body(body)
        world.update(0.016)
        self.assertAlmostEqual(body.rect.bottom, 480.0, places=3)
        self.assertEqual(body.velocity.y, 0.0)

    def test_impulse_bounces_up_then_lands(self):
        world = World(gravity=(0, 500), static_rects=(Rect(0, 480, 640, 20),))
        body = Body(position=(320, 440), size=(40, 40))
        body.apply_impulse((0, -200))
        world.add_body(body)
        for _ in range(120):
            world.update(0.016)
        self.assertAlmostEqual(body.rect.bottom, 480.0, places=3)
        self.assertEqual(body.velocity.y, 0.0)

    def test_fast_body_does_not_tunnel_through_ceiling(self):
        # A fast body flush under a thin ceiling must not jump clean through it.
        world = World(gravity=(0, 0), static_rects=(Rect(0, 0, 1000, 4),))
        body = Body(position=(0, 4), size=(10, 10), velocity=(0, -400))
        world.add_body(body)
        world.update(0.05)
        self.assertGreaterEqual(body.rect.top, 4.0 - 1e-6)
        self.assertEqual(body.velocity.y, 0.0)

    def test_fast_body_does_not_tunnel_through_floor(self):
        world = World(gravity=(0, 0), static_rects=(Rect(0, 40, 1000, 4),))
        body = Body(position=(0, 20), size=(10, 10), velocity=(0, 2000))
        world.add_body(body)
        world.update(0.05)
        self.assertLessEqual(body.rect.bottom, 40.0 + 1e-6)
        self.assertEqual(body.velocity.y, 0.0)

    def test_slow_ceiling_flush_contact_resolves(self):
        world = World(gravity=(0, 0), static_rects=(Rect(0, 0, 1000, 4),))
        body = Body(position=(0, 4), size=(10, 10), velocity=(0, -80))
        world.add_body(body)
        world.update(0.05)
        self.assertGreaterEqual(body.rect.top, 4.0 - 1e-6)
        self.assertEqual(body.velocity.y, 0.0)


class TestPublicExports(unittest.TestCase):
    def test_top_level_exports(self):
        self.assertIs(pydex_ge.Body, Body)
        self.assertIs(pydex_ge.World, World)

    def test_physics_exports(self):
        import pydex_ge.physics as physics

        self.assertIs(physics.Body, Body)
        self.assertIs(physics.World, World)


if __name__ == "__main__":
    unittest.main()
