"""Tests for the Part 3D public API exports."""

import unittest

import pydex_ge


class TestPublicExports3D(unittest.TestCase):
    def test_top_level_exports(self):
        for name in (
            "Vector3",
            "Quaternion",
            "Transform3D",
            "Camera3D",
            "Mesh",
            "Material",
            "Object3D",
            "DirectionalLight",
        ):
            self.assertTrue(hasattr(pydex_ge, name), name)
            self.assertIn(name, pydex_ge.__all__)

    def test_subpackage_exports(self):
        self.assertTrue(hasattr(pydex_ge.physics, "Vector3"))
        self.assertTrue(hasattr(pydex_ge.math, "Quaternion"))
        self.assertTrue(hasattr(pydex_ge.transform, "Transform3D"))
        self.assertTrue(hasattr(pydex_ge.core, "Camera3D"))
        for name in ("Mesh", "Material", "Object3D", "DirectionalLight"):
            self.assertTrue(hasattr(pydex_ge.graphics, name), name)

    def test_version_unchanged(self):
        self.assertEqual(pydex_ge.__version__, "1.0.0")

    def test_2d_exports_untouched(self):
        for name in ("Vector2", "Transform2D", "Camera", "Camera2D", "Sprite", "Scene", "World", "Body"):
            self.assertTrue(hasattr(pydex_ge, name), name)

    def test_constructable(self):
        self.assertIsInstance(pydex_ge.Vector3(1, 2, 3), pydex_ge.Vector3)
        self.assertIsInstance(pydex_ge.Quaternion.identity(), pydex_ge.Quaternion)
        self.assertIsInstance(pydex_ge.Transform3D(), pydex_ge.Transform3D)
        self.assertIsInstance(pydex_ge.Camera3D(), pydex_ge.Camera3D)
        self.assertIsInstance(pydex_ge.Mesh.cube(), pydex_ge.Mesh)
        self.assertIsInstance(pydex_ge.Material(), pydex_ge.Material)
        self.assertIsInstance(pydex_ge.Object3D(), pydex_ge.Object3D)
        self.assertIsInstance(pydex_ge.DirectionalLight(), pydex_ge.DirectionalLight)


if __name__ == "__main__":
    unittest.main()
