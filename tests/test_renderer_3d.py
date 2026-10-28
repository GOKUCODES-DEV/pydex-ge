"""Tests for the Part 3D renderer integration (begin_3d / draw_mesh / end_3d)."""

import unittest

from _stub_backend import StubRenderer

from pydex_ge import (
    Camera3D,
    ConfigurationError,
    Material,
    Mesh,
    Object3D,
    Renderer,
    Scene,
    Transform3D,
)


class TestRenderer3D(unittest.TestCase):
    def setUp(self):
        self.backend = StubRenderer()
        self.renderer = Renderer(self.backend)
        self.camera = Camera3D(800, 600)
        self.camera.set_viewport(800, 600)

    def test_draw_mesh_requires_active_camera(self):
        with self.assertRaises(ConfigurationError):
            self.renderer.draw_mesh(Mesh.cube())

    def test_end_3d_without_begin_raises(self):
        with self.assertRaises(RuntimeError):
            self.renderer.end_3d()

    def test_begin_3d_validates_camera_type(self):
        with self.assertRaises(ConfigurationError):
            self.renderer.begin_3d(object())

    def test_begin_3d_fills_viewport_from_renderer_size(self):
        renderer = Renderer(StubRenderer(), size=(640, 480))
        camera = Camera3D()
        self.assertIsNone(camera.width)
        renderer.begin_3d(camera)
        self.assertEqual(camera.width, 640.0)
        self.assertEqual(camera.height, 480.0)
        renderer.end_3d()

    def test_begin_3d_no_viewport_no_size_raises(self):
        camera = Camera3D()
        with self.assertRaises(ConfigurationError):
            self.renderer.begin_3d(camera)

    def test_draw_mesh_flushes_lines(self):
        self.renderer.begin_3d(self.camera)
        self.renderer.draw_mesh(Mesh.cube(), Transform3D(position=(0, 0, -6)), Material(color=(255, 0, 0)))
        self.renderer.draw_line_3d((0, 0, -6), (0, 0, -5), color=(0, 255, 0))
        self.renderer.end_3d()
        self.assertIsNone(self.renderer.active_camera3d)
        self.assertGreater(len(self.backend.lines), 0)
        self.assertTrue(any(line[4][0] == 0 and line[4][1] == 255 for line in self.backend.lines))

    def test_active_camera3d(self):
        self.renderer.begin_3d(self.camera)
        self.assertIs(self.renderer.active_camera3d, self.camera)
        self.renderer.end_3d()

    def test_disabled_camera_begin_is_noop(self):
        self.camera.enabled = False
        self.renderer.begin_3d(self.camera)
        self.assertIsNone(self.renderer.active_camera3d)
        with self.assertRaises(ConfigurationError):
            self.renderer.draw_mesh(Mesh.cube())

    def test_draw_mesh_type_validation(self):
        self.renderer.begin_3d(self.camera)
        with self.assertRaises(ConfigurationError):
            self.renderer.draw_mesh("nope")
        with self.assertRaises(ConfigurationError):
            self.renderer.draw_mesh(Mesh.cube(), transform="nope")
        with self.assertRaises(ConfigurationError):
            self.renderer.draw_mesh(Mesh.cube(), material="nope")
        self.renderer.end_3d()

    def test_draw_line_3d_clips_near_plane(self):
        self.renderer.begin_3d(self.camera)
        self.renderer.draw_line_3d((-10, 0, -0.05), (-10, 0, -30), color=(255, 0, 0))
        self.renderer.end_3d()
        self.assertEqual(len(self.backend.lines), 1)

    def test_draw_line_3d_fully_behind_near_plane_is_dropped(self):
        self.renderer.begin_3d(self.camera)
        self.renderer.draw_line_3d((-10, 0, 0.2), (-10, 0, -0.05), color=(255, 0, 0))
        self.renderer.end_3d()
        self.assertEqual(self.backend.lines, [])


class TestObject3DRenderLoop(unittest.TestCase):
    def test_scene_with_camera3d_draws_objects(self):
        backend = StubRenderer()
        renderer = Renderer(backend, size=(800, 600))
        camera = Camera3D()
        scene = Scene(camera3d=camera)
        cube = Object3D(mesh=Mesh.cube(), material=Material(color=(255, 0, 0)), transform=Transform3D(position=(0, 0, -6)))
        scene.add(cube)
        scene.draw(renderer)
        self.assertGreater(len(backend.lines), 0)

    def test_scene_2d_behavior_unchanged(self):
        backend = StubRenderer()
        renderer = Renderer(backend, size=(800, 600))
        scene = Scene()
        scene.add(Object3D(mesh=Mesh.cube(), transform=Transform3D(position=(0, 0, -6))))
        scene.draw(renderer)
        self.assertEqual(backend.lines, [])

    def test_scene_camera_takes_precedence(self):
        from pydex_ge import Camera

        backend = StubRenderer()
        renderer = Renderer(backend, size=(800, 600))
        camera2d = Camera(800, 600)
        camera3d = Camera3D()
        scene = Scene(camera=camera2d, camera3d=camera3d)
        scene.draw(renderer)
        self.assertIsNone(renderer.active_camera3d)


if __name__ == "__main__":
    unittest.main()
