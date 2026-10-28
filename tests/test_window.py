"""Tests for the Window abstraction (using the headless backend)."""

import unittest

from pydex_ge import ConfigurationError, Window
from pydex_ge.backend.null import NullBackend


class TestWindow(unittest.TestCase):
    def test_defaults(self):
        window = Window(backend=NullBackend())
        self.assertEqual(window.title, "PYDEX")
        self.assertEqual((window.width, window.height), (800, 600))
        self.assertTrue(window.closed)

    def test_custom_configuration(self):
        window = Window("Hello", 320, 240, backend=NullBackend())
        self.assertEqual(window.title, "Hello")
        self.assertEqual((window.width, window.height), (320, 240))

    def test_open_sets_title_setter(self):
        window = Window(backend=NullBackend())
        window.title = "Renamed"
        self.assertEqual(window.title, "Renamed")

    def test_open_and_close_state(self):
        window = Window(backend=NullBackend())
        self.assertTrue(window.closed)
        window.open()
        self.assertFalse(window.closed)
        window.close()
        self.assertTrue(window.closed)

    def test_close_is_idempotent(self):
        window = Window(backend=NullBackend())
        window.open()
        window.close()
        window.close()
        self.assertTrue(window.closed)

    def test_reopen_after_close(self):
        window = Window(backend=NullBackend())
        window.open()
        window.close()
        window.open()
        self.assertFalse(window.closed)
        window.close()

    def test_open_is_idempotent(self):
        window = Window(backend=NullBackend())
        window.open()
        window.open()
        self.assertFalse(window.closed)

    def test_empty_title_rejected(self):
        for bad in ("", "   "):
            with self.assertRaises(ConfigurationError):
                Window(bad, backend=NullBackend())

    def test_invalid_dimensions_rejected(self):
        for bad in (0, -1, 0.0, 1.5, True, "800"):
            with self.assertRaises(ConfigurationError):
                Window("t", bad, 600, backend=NullBackend())
            with self.assertRaises(ConfigurationError):
                Window("t", 600, bad, backend=NullBackend())

    def test_resize_updates_size(self):
        window = Window("t", 800, 600, backend=NullBackend())
        window.resize(1024, 768)
        self.assertEqual((window.width, window.height), (1024, 768))

    def test_resize_rejects_invalid_size(self):
        window = Window("t", 800, 600, backend=NullBackend())
        for bad in (0, -10, True, 1.5, "100"):
            with self.assertRaises(ConfigurationError):
                window.resize(bad, 600)
            with self.assertRaises(ConfigurationError):
                window.resize(600, bad)

    def test_renderer_requires_open_window(self):
        window = Window(backend=NullBackend())
        with self.assertRaises(RuntimeError):
            window.renderer

    def test_renderer_available_while_open(self):
        window = Window(backend=NullBackend())
        window.open()
        renderer = window.renderer
        self.assertIsNotNone(renderer)
        window.close()

    def test_renderer_clears_and_presents(self):
        window = Window(backend=NullBackend())
        window.open()
        renderer = window.renderer
        renderer.clear((20, 20, 25))
        renderer.present()
        window.close()


if __name__ == "__main__":
    unittest.main()