"""Tests for backend selection and the null backend."""

import os
import unittest

from pydex_ge.backend import NullBackend, select_backend
from pydex_ge.backend.sdl2 import SDL2Backend
from pydex_ge.exceptions import BackendError


class TestBackendSelection(unittest.TestCase):
    def test_null_backend_type(self):
        self.assertIsInstance(select_backend("null"), NullBackend)

    def test_unknown_backend_rejected(self):
        with self.assertRaises(BackendError):
            select_backend("opengl")

    def test_default_is_sdl2_when_installed(self):
        backend = select_backend()
        self.assertIsInstance(backend, SDL2Backend)

    def test_sdl2_available_in_this_environment(self):
        backend = SDL2Backend()
        self.assertTrue(backend.is_available())

    def test_sdl2_init_and_quit(self):
        backend = SDL2Backend()
        backend.init()
        backend.quit()
        backend.quit()  # idempotent

    def test_env_var_override_null(self):
        os.environ["PYDEX_BACKEND"] = "null"
        try:
            self.assertIsInstance(select_backend(), NullBackend)
        finally:
            os.environ.pop("PYDEX_BACKEND", None)


class TestNullBackend(unittest.TestCase):
    def test_lifecycle(self):
        backend = NullBackend()
        self.assertTrue(backend.is_available())
        backend.init()
        backend.quit()
        backend.quit()

    def test_no_events(self):
        from pydex_ge.backend.null import NullBackend

        self.assertEqual(NullBackend().poll_events(), [])

    def test_create_window_returns_null_handle(self):
        from pydex_ge.backend.null import NullWindow

        backend = NullBackend()
        window = backend.create_window("t", 10, 10)
        self.assertIsInstance(window, NullWindow)
        window.close()
        self.assertTrue(window.closed)


if __name__ == "__main__":
    unittest.main()