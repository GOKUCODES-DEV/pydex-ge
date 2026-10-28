"""Tests for the Part 12 deterministic 2D effects: Fade, Flash, and Tint."""

import unittest

from pydex_ge import ConfigurationError
from pydex_ge.graphics.effects import Fade, Flash, Tint


class TestFade(unittest.TestCase):
    def test_interpolation(self):
        fade = Fade(0, 255, 1.0)
        self.assertEqual(fade.alpha, 0)
        self.assertFalse(fade.finished)
        fade.update(0.25)
        self.assertEqual(fade.alpha, 64)
        fade.update(0.5)
        self.assertEqual(fade.alpha, 191)
        fade.update(0.25)
        self.assertEqual(fade.alpha, 255)
        self.assertTrue(fade.finished)
        self.assertEqual(fade.progress, 1.0)

    def test_finished_reaches_target_exactly(self):
        fade = Fade(255, 0, 2.0)
        fade.update(1.9)
        self.assertNotEqual(fade.alpha, 0)
        fade.update(0.2)
        self.assertEqual(fade.alpha, 0)
        self.assertTrue(fade.finished)

    def test_progress_clamps(self):
        fade = Fade(0, 100, 1.0)
        fade.update(5.0)
        self.assertEqual(fade.progress, 1.0)
        self.assertEqual(fade.alpha, 100)

    def test_properties(self):
        fade = Fade(10, 200, 1.5)
        self.assertEqual(fade.start_alpha, 10)
        self.assertEqual(fade.target_alpha, 200)
        self.assertEqual(fade.duration, 1.5)
        self.assertEqual(fade.time, 0.0)

    def test_validation(self):
        with self.assertRaises(ConfigurationError):
            Fade(0, 256, 1.0)
        with self.assertRaises(ConfigurationError):
            Fade(-1, 100, 1.0)
        with self.assertRaises(ConfigurationError):
            Fade(0, 100, 0)
        with self.assertRaises(ConfigurationError):
            Fade(0, 100, "long")
        fade = Fade(0, 100, 1.0)
        fade.update(0)  # dt=0 is a no-op, not an error
        self.assertEqual(fade.alpha, 0)
        with self.assertRaises(ConfigurationError):
            fade.update(-0.1)


class TestFlash(unittest.TestCase):
    def test_strength_decay(self):
        flash = Flash(1.0)
        self.assertEqual(flash.strength, 1.0)
        self.assertFalse(flash.finished)
        flash.update(0.25)
        self.assertAlmostEqual(flash.strength, 0.75)
        flash.update(0.5)
        self.assertAlmostEqual(flash.strength, 0.25)
        flash.update(0.25)
        self.assertEqual(flash.strength, 0.0)
        self.assertTrue(flash.finished)

    def test_color_default_and_custom(self):
        self.assertEqual(Flash(1.0).color, (255, 255, 255))
        self.assertEqual(Flash(1.0, (255, 0, 0)).color, (255, 0, 0))

    def test_validation(self):
        with self.assertRaises(ConfigurationError):
            Flash(0)
        with self.assertRaises(ConfigurationError):
            Flash(-1.0)
        with self.assertRaises(ConfigurationError):
            Flash("soon")
        with self.assertRaises(ConfigurationError):
            Flash(1.0, (300, 0, 0))
        flash = Flash(1.0)
        flash.update(0)
        self.assertEqual(flash.strength, 1.0)
        with self.assertRaises(ConfigurationError):
            flash.update(-0.1)


class TestTint(unittest.TestCase):
    def test_default_is_neutral(self):
        tint = Tint()
        self.assertEqual(tint.color, (255, 255, 255))

    def test_channels(self):
        tint = Tint((10, 20, 30))
        self.assertEqual(tint.r, 10)
        self.assertEqual(tint.g, 20)
        self.assertEqual(tint.b, 30)

    def test_setter_validates(self):
        tint = Tint()
        tint.color = (0, 128, 255)
        self.assertEqual(tint.color, (0, 128, 255))
        with self.assertRaises(ConfigurationError):
            tint.color = (1, 2)
        with self.assertRaises(ConfigurationError):
            tint.color = (1, 2, 300)

    def test_equality_and_repr(self):
        self.assertEqual(Tint((1, 2, 3)), Tint((1, 2, 3)))
        self.assertNotEqual(Tint((1, 2, 3)), Tint((1, 2, 4)))
        self.assertNotEqual(Tint(), "tint")
        self.assertIn("Tint", repr(Tint()))


if __name__ == "__main__":
    unittest.main()
