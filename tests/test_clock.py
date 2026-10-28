"""Tests for the Clock class."""

import unittest

from pydex_ge import Clock


class TestClock(unittest.TestCase):
    def test_first_tick_is_zero(self):
        self.assertEqual(Clock().tick(), 0.0)

    def test_tick_returns_non_negative(self):
        clock = Clock()
        clock.tick()
        self.assertGreaterEqual(clock.tick(), 0.0)

    def test_fps_property_before_tick_is_zero(self):
        self.assertEqual(Clock().fps, 0.0)

    def test_fps_cap_returns_small_positive_dt(self):
        clock = Clock()
        clock.tick(fps=1000)  # warm up
        dt = clock.tick(fps=1000)
        self.assertGreater(dt, 0.0)
        self.assertLess(dt, 1.0)

    def test_fps_property_after_tick(self):
        clock = Clock()
        clock.tick(fps=1000)
        clock.tick(fps=1000)
        self.assertIsInstance(clock.fps, float)
        self.assertGreater(clock.fps, 0.0)

    def test_get_time_does_not_decrease(self):
        clock = Clock()
        start = clock.get_time()
        clock.tick(fps=1000)
        self.assertGreaterEqual(clock.get_time(), start)

    def test_high_fps_cap_sleeps_for_at_least_target(self):
        # A 0.05 s cap must return ~0.05 s of elapsed time.
        clock = Clock()
        clock.tick()
        dt = clock.tick(fps=20)
        self.assertGreaterEqual(dt, 0.05)
        self.assertLess(dt, 1.0)


if __name__ == "__main__":
    unittest.main()