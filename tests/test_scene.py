"""Tests for the Scene class: object management and lifecycle forwarding."""

import os
import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import Camera2D, Label, Renderer, Scene, Sprite


class _Recorder:
    """Dummy object recording which lifecycle calls it received."""

    def __init__(self, name):
        self.name = name
        self.updates = []
        self.draws = 0
        self.events = []

    def update(self, dt):
        self.updates.append(dt)

    def draw(self, renderer):
        self.draws += 1
        self._renderer = renderer

    def handle_event(self, event):
        self.events.append(event)


class _UpdateOnly:
    def __init__(self):
        self.updates = 0

    def update(self, dt):
        self.updates += 1


class _DrawOnly:
    def __init__(self):
        self.draws = 0

    def draw(self, renderer):
        self.draws += 1


class _NoMethods:
    pass


class TestSceneConstruction(unittest.TestCase):
    def test_empty_scene(self):
        scene = Scene()
        self.assertEqual(len(scene), 0)
        self.assertEqual(list(scene), [])

    def test_scene_repr(self):
        scene = Scene()
        self.assertIn("Scene", repr(scene))


class TestSceneObjectManagement(unittest.TestCase):
    def setUp(self):
        self.scene = Scene()

    def test_add_returns_object(self):
        obj = object()
        self.assertIs(self.scene.add(obj), obj)

    def test_add_increments_length_and_iteration(self):
        a, b = object(), object()
        self.scene.add(a)
        self.scene.add(b)
        self.assertEqual(len(self.scene), 2)
        self.assertEqual(list(self.scene), [a, b])

    def test_contains(self):
        a = object()
        self.scene.add(a)
        self.assertIn(a, self.scene)
        self.assertNotIn(object(), self.scene)

    def test_remove_returns_true_and_removes(self):
        a = object()
        self.scene.add(a)
        self.assertTrue(self.scene.remove(a))
        self.assertEqual(len(self.scene), 0)
        self.assertNotIn(a, self.scene)

    def test_remove_absent_returns_false(self):
        self.assertFalse(self.scene.remove(object()))

    def test_remove_is_idempotent(self):
        a = object()
        self.scene.add(a)
        self.assertTrue(self.scene.remove(a))
        self.assertFalse(self.scene.remove(a))

    def test_clear_empties(self):
        self.scene.add(object())
        self.scene.add(object())
        self.scene.clear()
        self.assertEqual(len(self.scene), 0)
        self.assertEqual(list(self.scene), [])

    def test_iteration_is_insertion_order(self):
        objs = [_Recorder("a"), _Recorder("b"), _Recorder("c")]
        for obj in objs:
            self.scene.add(obj)
        self.assertEqual(list(self.scene), objs)


class TestSceneForwarding(unittest.TestCase):
    def setUp(self):
        self.scene = Scene()
        self.renderer = Renderer(StubRenderer())

    def test_update_forwards_with_dt(self):
        a, b = _Recorder("a"), _Recorder("b")
        self.scene.add(a)
        self.scene.add(b)
        self.scene.update(0.016)
        self.assertEqual(a.updates, [0.016])
        self.assertEqual(b.updates, [0.016])

    def test_update_skips_objects_without_update(self):
        plain = object()
        updater = _UpdateOnly()
        self.scene.add(plain)
        self.scene.add(updater)
        self.scene.update(0.5)
        self.assertEqual(updater.updates, 1)

    def test_draw_forwards_renderer(self):
        a, b = _Recorder("a"), _Recorder("b")
        self.scene.add(a)
        self.scene.add(b)
        self.scene.draw(self.renderer)
        self.assertEqual(a.draws, 1)
        self.assertEqual(b.draws, 1)
        self.assertIs(a._renderer, self.renderer)

    def test_draw_skips_objects_without_draw(self):
        drawer = _DrawOnly()
        self.scene.add(object())
        self.scene.add(drawer)
        self.scene.draw(self.renderer)
        self.assertEqual(drawer.draws, 1)

    def test_handle_event_forwards_event(self):
        a, b = _Recorder("a"), _Recorder("b")
        self.scene.add(a)
        self.scene.add(b)
        event = object()
        self.scene.handle_event(event)
        self.assertEqual(a.events, [event])
        self.assertEqual(b.events, [event])

    def test_handle_event_skips_objects_without_handler(self):
        recorder = _Recorder("a")
        self.scene.add(object())
        self.scene.add(recorder)
        event = object()
        self.scene.handle_event(event)
        self.assertEqual(recorder.events, [event])

    def test_clear_stops_forwarding(self):
        recorder = _Recorder("a")
        self.scene.add(recorder)
        self.scene.clear()
        self.scene.update(1.0)
        self.scene.draw(self.renderer)
        self.assertEqual(recorder.updates, [])
        self.assertEqual(recorder.draws, 0)


class TestSceneCameraIntegration(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._path = write_fixture(self._tmp.name, "tile.bmp", bmp_bytes(16, 16))
        self._font_path = os.path.join(self._tmp.name, "font.ttf")
        with open(self._font_path, "wb") as handle:
            handle.write(b"\x00\x01\x00\x00 fake ttf bytes")
        self.backend = StubBackend(image_sizes={self._path: (16, 16)})
        self.renderer = Renderer(StubRenderer())

    def _pixel_sprite(self):
        pixels = bytes((255, 0, 0, 255)) * (8 * 8)
        sprite = Sprite.from_pixels(8, 8, pixels)
        sprite.position = (400, 300)
        return sprite

    def test_scene_without_camera_draws_untransformed(self):
        scene = Scene()
        scene.add(self._pixel_sprite())
        scene.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (400, 300, 8, 8))

    def test_scene_with_camera_transforms_sprites(self):
        camera = Camera2D(800, 600, position=(400, 300), zoom=1.0)
        scene = Scene(camera=camera)
        scene.add(self._pixel_sprite())
        scene.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (400, 300, 8, 8))

    def test_scene_with_camera_transforms_offset_sprite(self):
        camera = Camera2D(800, 600, position=(400, 300), zoom=1.0)
        scene = Scene(camera=camera)
        sprite = self._pixel_sprite()
        sprite.position = (100, 100)
        scene.add(sprite)
        scene.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (100, 100, 8, 8))

    def test_scene_with_camera_scales_by_zoom(self):
        camera = Camera2D(800, 600, position=(400, 300), zoom=2.0)
        scene = Scene(camera=camera)
        sprite = self._pixel_sprite()
        sprite.position = (500, 300)
        scene.add(sprite)
        scene.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (600, 300, 16, 16))

    def test_label_stays_screen_space_under_camera(self):
        camera = Camera2D(800, 600, position=(400, 300), zoom=2.0)
        scene = Scene(camera=camera)
        label = Label("HI", font=self._font_path, position=(5, 6), backend=self.backend)
        scene.add(label)
        scene.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst[:2], (5, 6))

    def test_sprite_and_label_together(self):
        camera = Camera2D(800, 600, position=(400, 300), zoom=1.0)
        scene = Scene(camera=camera)
        scene.add(self._pixel_sprite())
        label = Label("HI", font=self._font_path, position=(5, 6), backend=self.backend)
        scene.add(label)
        scene.draw(self.renderer)
        draws = self.renderer._renderer.texture_draws
        self.assertEqual(len(draws), 2)
        self.assertEqual(draws[0][2], (400, 300, 8, 8))
        self.assertEqual(draws[1][2][:2], (5, 6))

    def test_disabled_camera_renders_untransformed(self):
        camera = Camera2D(800, 600, position=(400, 300))
        camera.enabled = False
        scene = Scene(camera=camera)
        sprite = self._pixel_sprite()
        sprite.position = (123, 45)
        scene.add(sprite)
        scene.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (123, 45, 8, 8))


class TestSceneLifecycleHooks(unittest.TestCase):
    def test_base_hooks_are_noops(self):
        scene = Scene()
        scene.on_enter()
        scene.on_exit()

    def test_subclass_hooks_called(self):
        class TrackingScene(Scene):
            def __init__(self):
                super().__init__()
                self.entered = 0
                self.exited = 0

            def on_enter(self):
                self.entered += 1

            def on_exit(self):
                self.exited += 1

        scene = TrackingScene()
        scene.on_enter()
        scene.on_enter()
        scene.on_exit()
        self.assertEqual(scene.entered, 2)
        self.assertEqual(scene.exited, 1)


class TestSceneWithExistingObjects(unittest.TestCase):
    def test_sprite_update_draw(self):
        scene = Scene()
        sprite = _UpdateOnly()
        scene.add(sprite)
        scene.update(0.1)
        self.assertEqual(sprite.updates, 1)


if __name__ == "__main__":
    unittest.main()
