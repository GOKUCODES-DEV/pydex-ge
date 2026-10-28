"""Tests for the Part 3D Mesh, Material and Object3D graphics types."""

import unittest

from pydex_ge import (
    ConfigurationError,
    Material,
    Mesh,
    Object3D,
    Quaternion,
    Transform3D,
    Vector3,
)


class TestMesh(unittest.TestCase):
    def test_triangle(self):
        mesh = Mesh.triangle((0, 0, 0), (1, 0, 0), (0, 1, 0))
        self.assertEqual(mesh.vertex_count, 3)
        self.assertEqual(mesh.triangle_count, 1)
        self.assertEqual(len(mesh.indices), 1)
        self.assertEqual(mesh.indices[0], (0, 1, 2))
        self.assertEqual(len(mesh.face_normals), 1)

    def test_quad(self):
        mesh = Mesh.quad((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))
        self.assertEqual(mesh.vertex_count, 4)
        self.assertEqual(mesh.triangle_count, 2)

    def test_cube(self):
        mesh = Mesh.cube()
        self.assertEqual(mesh.vertex_count, 8)
        self.assertEqual(mesh.triangle_count, 12)
        self.assertEqual(len(mesh.indices), 12)
        self.assertEqual(len(mesh.face_normals), 12)
        for index in range(12):
            self.assertEqual(len(mesh.indices[index]), 3)
        self.assertAlmostEqual(mesh.bounding_radius, (3 ** 0.5) / 2)

    def test_cube_size(self):
        mesh = Mesh.cube(size=2)
        self.assertAlmostEqual(mesh.bounding_radius, 3 ** 0.5)

    def test_face_normals_computed(self):
        mesh = Mesh.triangle((0, 0, 0), (1, 0, 0), (0, 1, 0))
        normal = mesh.face_normals[0]
        self.assertAlmostEqual(normal.z, 1.0)
        self.assertAlmostEqual(normal.length, 1.0)

    def test_invalid_indices(self):
        with self.assertRaises(ConfigurationError):
            Mesh([Vector3(0, 0, 0)], [(0, 1, 2)])
        with self.assertRaises(ConfigurationError):
            Mesh([Vector3(0, 0, 0)], [("a", "b", "c")])
        with self.assertRaises(ConfigurationError):
            Mesh([Vector3(0, 0, 0)], [(0, 1)])
        with self.assertRaises(ConfigurationError):
            Mesh([Vector3(0, 0, 0), Vector3(1, 0, 0)], [(0, 1, 2)])

    def test_no_triangles(self):
        with self.assertRaises(ConfigurationError):
            Mesh([Vector3(0, 0, 0)], [])

    def test_uv_validation(self):
        mesh = Mesh(
            [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(0, 1, 0)],
            [(0, 1, 2)],
            uvs=[(0, 0), (1, 0), (0, 1)],
        )
        self.assertEqual(mesh.uvs[0], (0.0, 0.0))
        with self.assertRaises(ConfigurationError):
            Mesh([Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(0, 1, 0)], [(0, 1, 2)], uvs=[(0, 0)])


class TestMaterial(unittest.TestCase):
    def test_defaults(self):
        m = Material()
        self.assertEqual(m.color, (255, 255, 255))
        self.assertEqual(m.opacity, 1.0)
        self.assertIsNone(m.texture)
        self.assertEqual(m.emission, (0, 0, 0))

    def test_values(self):
        m = Material(color=(200, 80, 40), opacity=0.5, emission=(10, 0, 0))
        self.assertEqual(m.color, (200, 80, 40))
        self.assertEqual(m.opacity, 0.5)
        self.assertEqual(m.emission, (10, 0, 0))

    def test_invalid_color(self):
        with self.assertRaises(ConfigurationError):
            Material(color=(300, 0, 0))
        with self.assertRaises(ConfigurationError):
            Material(color=(1, 2))

    def test_invalid_opacity(self):
        with self.assertRaises(ConfigurationError):
            Material(opacity=1.5)
        with self.assertRaises(ConfigurationError):
            Material(opacity=-0.1)
        with self.assertRaises(ConfigurationError):
            Material(opacity="high")

    def test_copy(self):
        m = Material(color=(1, 2, 3))
        c = m.copy()
        self.assertEqual(c.color, (1, 2, 3))
        self.assertEqual(c.opacity, m.opacity)


class TestObject3D(unittest.TestCase):
    def test_defaults(self):
        obj = Object3D()
        self.assertIsNone(obj.mesh)
        self.assertIsInstance(obj.material, Material)
        self.assertIsInstance(obj.transform, Transform3D)
        self.assertTrue(obj.visible)
        self.assertTrue(obj.enabled)
        self.assertEqual(obj.z, 0.0)

    def test_construction(self):
        transform = Transform3D(position=(0, 0, -5))
        obj = Object3D(
            mesh=Mesh.cube(),
            material=Material(color=(200, 80, 40)),
            transform=transform,
        )
        self.assertEqual(obj.mesh.triangle_count, 12)
        self.assertEqual(obj.material.color, (200, 80, 40))
        self.assertIs(obj.transform, transform)

    def test_transform_convenience(self):
        obj = Object3D()
        obj.position = (1, 2, 3)
        self.assertEqual(obj.position, Vector3(1, 2, 3))
        obj.rotation = Quaternion.from_euler(0, 45, 0)
        self.assertAlmostEqual(obj.rotation_euler[1], 45.0, places=6)
        obj.move(1, 1, 1)
        self.assertEqual(obj.position, Vector3(2, 3, 4))

    def test_invalid_assignments(self):
        obj = Object3D()
        with self.assertRaises(ConfigurationError):
            obj.mesh = "nope"
        with self.assertRaises(ConfigurationError):
            obj.material = "nope"
        with self.assertRaises(ConfigurationError):
            obj.transform = "nope"

    def test_draw_noop_without_mesh(self):
        class FakeRenderer:
            def __init__(self):
                self.calls = 0

            def draw_mesh(self, *args):
                self.calls += 1

        renderer = FakeRenderer()
        Object3D().draw(renderer)
        self.assertEqual(renderer.calls, 0)

    def test_draw_hidden_or_disabled(self):
        class FakeRenderer:
            def __init__(self):
                self.calls = 0

            def draw_mesh(self, *args):
                self.calls += 1

        obj = Object3D(mesh=Mesh.cube())
        for flag_name in ("visible", "enabled"):
            renderer = FakeRenderer()
            setattr(obj, flag_name, False)
            obj.draw(renderer)
            self.assertEqual(renderer.calls, 0)
            setattr(obj, flag_name, True)

    def test_draw_forwards_to_renderer(self):
        class FakeRenderer:
            def __init__(self):
                self.args = None
                self.active_camera3d = object()

            def draw_mesh(self, mesh, transform, material):
                self.args = (mesh, transform, material)

        mesh = Mesh.cube()
        material = Material()
        obj = Object3D(mesh=mesh, material=material)
        renderer = FakeRenderer()
        obj.draw(renderer)
        self.assertIs(renderer.args[0], mesh)
        self.assertIs(renderer.args[1], obj.transform)
        self.assertIs(renderer.args[2], material)


if __name__ == "__main__":
    unittest.main()
