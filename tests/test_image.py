"""Tests for pydex_ge.Image loading via the headless null backend."""

import os
import tempfile
import unittest

from _image_fixtures import (
    PNG_SIGNATURE,
    bmp_bytes,
    jpeg_bytes,
    png_bytes,
    write_fixture,
)

from pydex_ge import Image
from pydex_ge.backend.null import NullBackend
from pydex_ge.exceptions import BackendError, ConfigurationError


class TestImageLoading(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, name: str, data: bytes) -> str:
        return write_fixture(self._dir, name, data)

    def test_load_bmp_dimensions(self):
        path = self._write("img.bmp", bmp_bytes(40, 30))
        image = Image(path, backend=NullBackend())
        self.assertEqual((image.width, image.height), (40, 30))

    def test_load_png_dimensions(self):
        path = self._write("img.png", png_bytes(64, 48))
        image = Image(path, backend=NullBackend())
        self.assertEqual((image.width, image.height), (64, 48))

    def test_load_jpeg_dimensions(self):
        path = self._write("img.jpg", jpeg_bytes(128, 96))
        image = Image(path, backend=NullBackend())
        self.assertEqual((image.width, image.height), (128, 96))

    def test_missing_file_raises_backend_error(self):
        with self.assertRaises(BackendError):
            Image(os.path.join(self._dir, "nope.png"), backend=NullBackend())

    def test_empty_path_rejected(self):
        for bad in ("", "   ", 123, None):
            with self.assertRaises(ConfigurationError):
                Image(bad, backend=NullBackend())

    def test_corrupt_file_raises_backend_error(self):
        path = self._write("broken.png", PNG_SIGNATURE + b"garbage")
        with self.assertRaises(BackendError):
            Image(path, backend=NullBackend())

    def test_unsupported_format_raises_backend_error(self):
        path = self._write("data.txt", b"not an image")
        with self.assertRaises(BackendError):
            Image(path, backend=NullBackend())

    def test_destroy_is_idempotent(self):
        path = self._write("img.bmp", bmp_bytes(4, 4))
        image = Image(path, backend=NullBackend())
        image.destroy()
        image.destroy()
        with self.assertRaises(RuntimeError):
            image.width
        with self.assertRaises(RuntimeError):
            image.height


if __name__ == "__main__":
    unittest.main()