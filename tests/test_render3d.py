"""Tests for the Part 3D CPU rendering pipeline (projection, lighting, raster)."""

import unittest

from pydex_ge.core.camera3d import Camera3D
from pydex_ge.core.render3d import (
    build_triangles,
    clip_line_to_near,
    fill_triangle,
    shade_color,
    transform_point_to_world,
)
from pydex_ge.graphics.light import DirectionalLight
from pydex_ge.graphics.material import Material
from pydex_ge.graphics.mesh import Mesh
from pydex_ge.physics.vector3 import Vector3
from pydex_ge.transform.transform3d import Transform3D


def make_camera():
    camera = Camera3D(800, 600)
    camera.set_viewport(800, 600)
    return camera


class TestTransformPointToWorld(unittest.TestCase):
    def test_identity(self):
        result = transform_point_to_world(Transform3D(), Vector3(1, 2, 3))
        self.assertEqual(result, Vector3(1, 2, 3))

    def test_position_offset(self):
        t = Transform3D(position=(5, 0, 0))
        result = transform_point_to_world(t, Vector3(1, 2, 3))
        self.assertEqual(result, Vector3(6, 2, 3))

    def test_scale(self):
        t = Transform3D(scale=(2, 1, 1))
        result = transform_point_to_world(t, Vector3(1, 1, 1))
        self.assertEqual(result, Vector3(2, 1, 1))

    def test_origin_pivot(self):
        t = Transform3D(position=(10, 0, 0))
        result = transform_point_to_world(t, Vector3(0, 0, 0))
        self.assertEqual(result, Vector3(10, 0, 0))
        t.origin = (1, 0, 0)
        result = transform_point_to_world(t, Vector3(1, 0, 0))
        self.assertEqual(result, Vector3(10, 0, 0))


class TestShadeColor(unittest.TestCase):
    def test_unlit_uses_material_color(self):
        self.assertEqual(shade_color(Material(color=(200, 80, 40)), Vector3(0, 1, 0), None), (200, 80, 40))

    def test_disabled_light_unlit(self):
        light = DirectionalLight()
        light.enabled = False
        self.assertEqual(shade_color(Material(color=(100, 100, 100)), Vector3(0, 1, 0), light), (100, 100, 100))

    def test_light_facing_direction(self):
        light = DirectionalLight(direction=(0, -1, 0))
        color = shade_color(Material(color=(255, 255, 255)), Vector3(0, 1, 0), light)
        self.assertEqual(color, (255, 255, 255))
        dark = shade_color(Material(color=(255, 255, 255)), Vector3(0, -1, 0), light)
        self.assertEqual(dark, (0, 0, 0))

    def test_intensity_scales(self):
        light = DirectionalLight(direction=(0, -1, 0), intensity=0.5)
        color = shade_color(Material(color=(200, 100, 50)), Vector3(0, 1, 0), light)
        self.assertEqual(color, (100, 50, 25))

    def test_emission_adds(self):
        material = Material(color=(0, 0, 0), emission=(50, 0, 0))
        color = shade_color(material, Vector3(0, 1, 0), None)
        self.assertEqual(color, (50, 0, 0))

    def test_channels_clamped(self):
        light = DirectionalLight(direction=(0, -1, 0), intensity=1.0)
        color = shade_color(Material(color=(200, 200, 200), emission=(100, 100, 100)), Vector3(0, 1, 0), light)
        self.assertEqual(color, (255, 255, 255))


class TestBuildTriangles(unittest.TestCase):
    def test_cube_front_faces_projected(self):
        camera = make_camera()
        mesh = Mesh.cube(size=2)
        transform = Transform3D(position=(0, 0, -6))
        records = build_triangles(camera, mesh, transform, Material(color=(255, 0, 0)), None)
        self.assertGreater(len(records), 0)
        for record in records:
            for point in record[:3]:
                self.assertIsNotNone(point)
                self.assertEqual(len(point), 3)
            self.assertGreater(record[4], 0)

    def test_records_sorted_farthest_first(self):
        camera = make_camera()
        mesh = Mesh.cube(size=2)
        transform = Transform3D(position=(0, 0, -6))
        records = build_triangles(camera, mesh, transform, Material(), None)
        depths = [record[4] for record in records]
        self.assertEqual(depths, sorted(depths, reverse=True))

    def test_behind_camera_no_triangles(self):
        camera = make_camera()
        mesh = Mesh.cube()
        transform = Transform3D(position=(0, 0, 5))
        records = build_triangles(camera, mesh, transform, Material(), None)
        self.assertEqual(records, [])

    def test_lit_color_changes(self):
        camera = make_camera()
        mesh = Mesh.cube(size=2)
        transform = Transform3D(position=(0, 0, -6))
        unlit = build_triangles(camera, mesh, transform, Material(color=(255, 255, 255)), None)
        light = DirectionalLight(direction=(0, 0, 1))
        lit = build_triangles(camera, mesh, transform, Material(color=(255, 255, 255)), light)
        self.assertGreater(len(unlit), 0)
        self.assertEqual(len(lit), len(unlit))

    def test_near_plane_clips_angled_triangle_instead_of_dropping(self):
        camera = make_camera()
        camera.position = (0, 0.6, 0)
        camera.rotation = camera.rotation.from_euler(0, -10, 0)
        floor = Mesh.quad((-3, 0, -3), (3, 0, -3), (3, 0, 3), (-3, 0, 3))
        records = build_triangles(camera, floor, Transform3D(), Material(), None)
        self.assertGreater(len(records), 0)
        for record in records:
            for point in record[:3]:
                self.assertGreater(point[2], 0)

    def test_cube_near_plane_still_renders_when_any_face_visible(self):
        camera = make_camera()
        mesh = Mesh.cube(size=2)
        transform = Transform3D(position=(0, 0, -1.05))
        records = build_triangles(camera, mesh, transform, Material(), None)
        self.assertEqual(records, [])
        transform = Transform3D(position=(0, 0, -1.2))
        records = build_triangles(camera, mesh, transform, Material(), None)
        self.assertGreater(len(records), 0)


class TestClipLineToNear(unittest.TestCase):
    def test_fully_in_front_unchanged(self):
        start, end = Vector3(0, 0, -1), Vector3(0, 0, -30)
        self.assertEqual(clip_line_to_near(start, end, 0.1), (start, end))

    def test_fully_behind_returns_none(self):
        start, end = Vector3(0, 0, 0.2), Vector3(0, 0, -0.05)
        self.assertIsNone(clip_line_to_near(start, end, 0.1))

    def test_straddling_is_cut_at_near_plane(self):
        start, end = Vector3(0, 0, -0.05), Vector3(0, 0, -30)
        clipped_start, clipped_end = clip_line_to_near(start, end, 0.1)
        self.assertAlmostEqual(clipped_start.z, -0.1)
        self.assertEqual(clipped_end, end)

    def test_straddling_reverse_direction(self):
        start, end = Vector3(0, 0, -30), Vector3(0, 0, -0.05)
        clipped_start, clipped_end = clip_line_to_near(start, end, 0.1)
        self.assertEqual(clipped_start, start)
        self.assertAlmostEqual(clipped_end.z, -0.1)


class TestFillTriangle(unittest.TestCase):
    def test_small_triangle_draws_lines(self):
        lines = []

        def draw_line(x1, y1, x2, y2, color):
            lines.append((x1, y1, x2, y2, color))

        record = ((0, 0, 1), (4, 4, 1), (4, 0, 1), (255, 0, 0), 1.0)
        fill_triangle(record, draw_line)
        self.assertGreater(len(lines), 0)
        for x1, y1, x2, y2, color in lines:
            self.assertEqual(y1, y2)  # horizontal spans
            self.assertEqual(color, (255, 0, 0, 255))

    def test_degenerate_triangle_draws_nothing(self):
        lines = []

        def draw_line(*args):
            lines.append(args)

        record = ((0, 0, 1), (0, 0, 1), (0, 0, 1), (255, 255, 255), 1.0)
        fill_triangle(record, draw_line)
        self.assertEqual(lines, [])


if __name__ == "__main__":
    unittest.main()
