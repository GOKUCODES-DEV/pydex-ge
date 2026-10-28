"""Tests that the package, core modules, and public API import cleanly."""

import unittest


class TestPackageImports(unittest.TestCase):
    def test_package_import(self):
        import pydex_ge

        self.assertTrue(hasattr(pydex_ge, "__version__"))
        self.assertIsInstance(pydex_ge.__version__, str)

    def test_core_module_imports(self):
        import pydex_ge.core
        import pydex_ge.core.clock
        import pydex_ge.core.events
        import pydex_ge.core.game
        import pydex_ge.core.window

        self.assertIsNotNone(pydex_ge.core)

    def test_backend_module_imports(self):
        import pydex_ge.backend
        import pydex_ge.backend.base
        import pydex_ge.backend.null
        import pydex_ge.backend.sdl2

        self.assertIsNotNone(pydex_ge.backend)

    def test_public_api_exports_only_real_classes(self):
        from pydex_ge import (
            Animation,
            Body,
            Camera,
            Camera2D,
            Clock,
            Event,
            EventManager,
            Game,
            Rect,
            Scene,
            SceneManager,
            Vector2,
            Window,
            World,
        )

        for cls in (Game, Window, Clock, EventManager, Event, Rect, Vector2,
                    Body, World, Animation, Camera, Camera2D, Scene, SceneManager):
            self.assertIsInstance(cls, type)

    def test_scene_modules_import(self):
        import pydex_ge.scene
        import pydex_ge.scene.manager
        import pydex_ge.scene.scene
        from pydex_ge import Scene, SceneManager

        self.assertIs(pydex_ge.scene.scene.Scene, Scene)
        self.assertIs(pydex_ge.scene.manager.SceneManager, SceneManager)

    def test_camera_and_animation_modules_import(self):
        import pydex_ge.core.camera
        import pydex_ge.graphics.animation
        from pydex_ge import Camera, Camera2D

        self.assertIs(pydex_ge.core.camera.Camera, Camera)
        self.assertIs(pydex_ge.core.camera.Camera2D, Camera2D)

    def test_exception_hierarchy(self):
        from pydex_ge import BackendError, ConfigurationError, PydexError

        self.assertTrue(issubclass(ConfigurationError, PydexError))
        self.assertTrue(issubclass(BackendError, PydexError))

    def test_placeholder_subsystems_are_importable(self):
        import pydex_ge.assets
        import pydex_ge.audio
        import pydex_ge.graphics
        import pydex_ge.input
        import pydex_ge.physics
        import pydex_ge.scene

        for module in (pydex_ge.assets, pydex_ge.audio, pydex_ge.graphics,
                       pydex_ge.input, pydex_ge.physics, pydex_ge.scene):
            self.assertIsNotNone(module)

    def test_graphics_exports_animation(self):
        import pydex_ge.graphics as graphics
        from pydex_ge import Animation

        self.assertIs(graphics.Animation, Animation)

    def test_physics_api(self):
        import pydex_ge.physics as physics
        from pydex_ge import Body, Rect, Vector2, World

        self.assertIs(physics.Vector2, Vector2)
        self.assertIs(physics.Rect, Rect)
        self.assertIs(physics.Body, Body)
        self.assertIs(physics.World, World)
        for name in ("point_in_rect", "rects_overlap", "circles_overlap",
                     "point_in_circle", "circle_rect_overlap"):
            self.assertTrue(callable(getattr(physics, name)))


if __name__ == "__main__":
    unittest.main()