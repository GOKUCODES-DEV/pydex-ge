"""Tests for Part 3D Scene integration (camera3d attribute, object coexistence)."""

import unittest

from _stub_backend import StubRenderer

from pydex_ge import (
    Camera,
    Camera3D,
    Mesh,
    Object3D,
    Renderer,
    Scene,
    Transform3D,
    Vector3,
)


class TestScene3D(unittest.TestCase):
    def test_camera3d_defaults_none(self):
        scene = Scene()
        self.assertIsNone(scene.camera3d)
        self.assertIsNone(scene.camera)

    def test_camera3d_constructor(self):
        camera = Camera3D()
        scene = Scene(camera3d=camera)
        self.assertIs(scene.camera3d, camera)

    def test_scene_draw_uses_3d_path(self):
        backend = StubRenderer()
        renderer = Renderer(backend, size=(800, 600))
        scene = Scene(camera3d=Camera3D())
        scene.add(Object3D(mesh=Mesh.cube(), transform=Transform3D(position=(0, 0, -6))))
        scene.draw(renderer)
        self.assertGreater(len(backend.lines), 0)

    def test_2d_scene_with_3d_object_does_not_crash(self):
        backend = StubRenderer()
        renderer = Renderer(backend)
        scene = Scene()
        scene.add(Object3D(mesh=Mesh.cube()))
        scene.draw(renderer)  # must not raise
        self.assertEqual(backend.lines, [])

    def test_2d_camera_still_works_alongside(self):
        backend = StubRenderer()
        renderer = Renderer(backend)
        scene = Scene(camera=Camera(800, 600))
        scene.draw(renderer)
        self.assertIsNone(renderer.active_camera3d)

    def test_update_forwards_to_3d_objects(self):
        class RotatingCube(Object3D):
            def __init__(self):
                super().__init__(mesh=Mesh.cube())
                self.updates = 0

            def update(self, dt):
                self.updates += 1
                self.position = (0, 0, -5)

        scene = Scene(camera3d=Camera3D())
        cube = RotatingCube()
        scene.add(cube)
        scene.update(0.016)
        self.assertEqual(cube.updates, 1)
        self.assertEqual(cube.position, Vector3(0, 0, -5))

    def test_scene_camera3d_attribute_assignable(self):
        scene = Scene()
        camera = Camera3D()
        scene.camera3d = camera
        self.assertIs(scene.camera3d, camera)

    def test_mixed_2d_3d_scene_draws(self):
        backend = StubRenderer()
        renderer = Renderer(backend, size=(800, 600))
        scene = Scene(camera3d=Camera3D())
        scene.add(Object3D(mesh=Mesh.cube(), transform=Transform3D(position=(0, 0, -6))))

        class SpriteLike:
            def __init__(self):
                self.draws = 0

            def draw(self, renderer):
                self.draws += 1

        sprite = SpriteLike()
        scene.add(sprite)
        scene.draw(renderer)
        self.assertEqual(sprite.draws, 1)
        self.assertGreater(len(backend.lines), 0)


if __name__ == "__main__":
    unittest.main()
