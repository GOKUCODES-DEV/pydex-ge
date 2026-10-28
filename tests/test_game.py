"""Tests for the Game class, using the headless backend."""

import os
import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend

import pydex_ge
from pydex_ge import (
    ConfigurationError,
    EventType,
    Game,
    Label,
    Scene,
    SceneManager,
    Sprite,
)
from pydex_ge.backend.base import BackendEvent
from pydex_ge.backend.null import NullBackend


class TestGame(unittest.TestCase):
    def test_construction(self):
        game = Game("Test Game", 640, 480, backend=NullBackend())
        self.assertEqual(game.window.title, "Test Game")
        self.assertEqual((game.window.width, game.window.height), (640, 480))
        self.assertEqual(game.fps, 60)
        self.assertIsNotNone(game.clock)
        self.assertIsNotNone(game.events)

    def test_defaults(self):
        game = Game(backend=NullBackend())
        self.assertEqual(game.window.title, "PYDEX")
        self.assertEqual((game.window.width, game.window.height), (800, 600))

    def test_invalid_fps_rejected(self):
        for bad in (0, -1, True):
            with self.assertRaises(ConfigurationError):
                Game(backend=NullBackend(), fps=bad)

    def test_run_headless_completes(self):
        game = Game(backend=NullBackend())
        game.run(max_frames=3)
        self.assertTrue(game.window.closed)

    def test_run_can_be_called_twice(self):
        game = Game(backend=NullBackend())
        game.run(max_frames=2)
        game.run(max_frames=2)
        self.assertTrue(game.window.closed)

    def test_run_invokes_hooks(self):
        class CountingGame(Game):
            def __init__(self):
                super().__init__(backend=NullBackend())
                self.updates = 0
                self.draws = 0

            def update(self, dt):
                self.updates += 1

            def draw(self):
                self.draws += 1

        game = CountingGame()
        game.run(max_frames=10)
        self.assertEqual(game.updates, 10)
        self.assertEqual(game.draws, 10)

    def test_close_stops_loop_early(self):
        class StopperGame(Game):
            def __init__(self):
                super().__init__(backend=NullBackend())
                self.updates = 0

            def update(self, dt):
                self.updates += 1
                self.close()

        game = StopperGame()
        game.run(max_frames=100)
        self.assertEqual(game.updates, 1)
        self.assertTrue(game.window.closed)

    def test_close_before_run_is_safe(self):
        game = Game(backend=NullBackend())
        game.close()
        self.assertTrue(game.window.closed)

    def test_default_background(self):
        game = Game(backend=NullBackend())
        self.assertEqual(game.background, (0, 0, 0))

    def test_background_setter_validates(self):
        game = Game(backend=NullBackend())
        game.background = (20, 20, 25)
        self.assertEqual(game.background, (20, 20, 25))
        for bad in ((0, 0), (0, 0, 0, 0), (0, 0, 256), (0, 0, -1), "red", 1.5, True):
            with self.assertRaises(ConfigurationError):
                game.background = bad

    def test_run_clears_and_presents_each_frame(self):
        backend = StubBackend()
        game = Game(backend=backend)
        game.background = (10, 20, 30)
        game.run(max_frames=3)
        renderer = backend.renderers[0]
        self.assertEqual(renderer.presents, 3)
        self.assertEqual(renderer.clears[0], (10, 20, 30, 255))

    def test_window_resize_event_updates_size(self):
        backend = StubBackend(
            [BackendEvent("window_resized", {"width": 640, "height": 480})]
        )
        game = Game(backend=backend)
        game.run(max_frames=1)
        self.assertEqual((game.window.width, game.window.height), (640, 480))

    def test_window_close_event_ends_loop(self):
        class Runner(Game):
            def __init__(self, backend):
                super().__init__(backend=backend)
                self.updates = 0

            def update(self, dt):
                self.updates += 1

        backend = StubBackend([BackendEvent("window_close")])
        game = Runner(backend)
        game.run(max_frames=100)
        self.assertEqual(game.updates, 0)
        self.assertTrue(game.window.closed)

    def test_renderer_property_matches_window_renderer(self):
        game = Game(backend=NullBackend())
        game.window.open()
        self.assertIs(game.renderer, game.window.renderer)
        game.window.close()

    def test_renderer_property_requires_open_window(self):
        game = Game(backend=NullBackend())
        with self.assertRaises(RuntimeError):
            game.renderer

    def test_setup_hook_runs_without_init(self):
        class SetupGame(Game):
            def setup(self):
                self.screen = "Snake", 500, 400
                self.fps = 8
                self.background = (10, 20, 30)

        game = SetupGame(backend=NullBackend())
        self.assertEqual(game.window.title, "Snake")
        self.assertEqual((game.window.width, game.window.height), (500, 400))
        self.assertEqual(game.fps, 8)
        self.assertEqual(game.background, (10, 20, 30))

    def test_setup_screen_with_fps(self):
        class SetupGame(Game):
            def setup(self):
                self.screen = "Game", 320, 240, 15

        game = SetupGame(backend=NullBackend())
        self.assertEqual(game.screen, ("Game", 320, 240, 15))

    def test_setup_preserves_defaults_when_unset(self):
        class SetupGame(Game):
            def setup(self):
                pass

        game = SetupGame(backend=NullBackend())
        self.assertEqual(game.screen, ("PYDEX", 800, 600, 60))

    def test_base_game_setup_is_noop(self):
        game = Game(backend=NullBackend())
        self.assertEqual(game.screen, ("PYDEX", 800, 600, 60))

    def test_screen_setter_rejects_bad_length(self):
        class SetupGame(Game):
            def setup(self):
                self.screen = "Only Title"

        with self.assertRaises(ConfigurationError):
            SetupGame(backend=NullBackend())

    def test_screen_setter_rejects_bad_fps(self):
        class SetupGame(Game):
            def setup(self):
                self.screen = "Game", 100, 100, "high"

        with self.assertRaises(ConfigurationError):
            SetupGame(backend=NullBackend())


class TestGameFps(unittest.TestCase):
    """Frame-rate configuration: capped modes and unlimited (None)."""

    def test_default_fps(self):
        game = Game(backend=NullBackend())
        self.assertEqual(game.fps, 60)

    def test_capped_fps_modes(self):
        for value in (24, 60, 120):
            game = Game(backend=NullBackend(), fps=value)
            self.assertEqual(game.fps, value)

    def test_fps_settable(self):
        game = Game(backend=NullBackend())
        game.fps = 24
        self.assertEqual(game.fps, 24)
        game.fps = 120
        self.assertEqual(game.fps, 120)

    def test_unlimited_fps(self):
        game = Game(backend=NullBackend(), fps=None)
        self.assertIsNone(game.fps)

    def test_set_unlimited_at_runtime(self):
        game = Game(backend=NullBackend())
        game.fps = None
        self.assertIsNone(game.fps)

    def test_invalid_fps_rejected_on_property(self):
        game = Game(backend=NullBackend())
        for bad in (0, -1, True, "high"):
            with self.assertRaises(ConfigurationError):
                game.fps = bad

    def test_invalid_fps_rejected_on_construction(self):
        for bad in (0, -1, True, "high"):
            with self.assertRaises(ConfigurationError):
                Game(backend=NullBackend(), fps=bad)

    def test_capped_modes_run(self):
        for value in (24, 60, 120):
            game = Game(backend=NullBackend(), fps=value)
            game.run(max_frames=3)
            self.assertTrue(game.window.closed)

    def test_unlimited_run_keeps_dt_usable(self):
        class DtGame(Game):
            def __init__(self):
                super().__init__(backend=NullBackend(), fps=None)
                self.dts = []

            def update(self, dt):
                self.dts.append(dt)

        game = DtGame()
        game.run(max_frames=6)
        self.assertEqual(len(game.dts), 6)
        self.assertTrue(all(dt >= 0 for dt in game.dts))
        self.assertGreater(max(game.dts), 0)


class TestInputLabelIntegration(unittest.TestCase):
    """keyboard event -> Input -> game code -> label text change."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.font_path = os.path.join(self.tmp.name, "font.ttf")
        with open(self.font_path, "wb") as handle:
            handle.write(b"\x00\x01\x00\x00 fake ttf bytes")

    def test_key_press_changes_label(self):
        class PressGame(Game):
            def __init__(self, backend, font_path):
                super().__init__(backend=backend)
                self.label = pydex_ge.Label("Press E", font=font_path, backend=backend)
                self.changed = False

            def update(self, dt):
                if self.input.is_key_pressed("e") and not self.changed:
                    self.label.text = "E was pressed!"
                    self.changed = True
                self.close()

        backend = StubBackend([BackendEvent("key_down", {"key": "e", "repeat": False})])
        game = PressGame(backend, self.font_path)
        game.run(max_frames=10)
        self.assertTrue(game.changed)
        self.assertEqual(game.label.text, "E was pressed!")

    def test_no_input_means_no_change(self):
        class QuietGame(Game):
            def __init__(self, backend, font_path):
                super().__init__(backend=backend)
                self.label = pydex_ge.Label("Press E", font=font_path, backend=backend)

            def update(self, dt):
                if self.input.is_key_pressed("e"):
                    self.label.text = "E was pressed!"
                self.close()

        backend = StubBackend()
        game = QuietGame(backend, self.font_path)
        game.run(max_frames=10)
        self.assertEqual(game.label.text, "Press E")


class TestSceneGameIntegration(unittest.TestCase):
    """Game -> SceneManager -> Scene -> Sprite/Label/Input integration."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._path = write_fixture(self.tmp.name, "icon.bmp", bmp_bytes(16, 16))
        self._font_path = os.path.join(self.tmp.name, "font.ttf")
        with open(self._font_path, "wb") as handle:
            handle.write(b"\x00\x01\x00\x00 fake ttf bytes")

    def test_game_owns_a_scene_manager(self):
        game = Game(backend=NullBackend())
        self.assertIsInstance(game.scenes, SceneManager)
        self.assertIsNone(game.scenes.current)

    def test_current_scene_updated_and_drawn_each_frame(self):
        class RecordingScene(Scene):
            def __init__(self):
                super().__init__()
                self.updates = 0
                self.draws = 0

            def update(self, dt):
                self.updates += 1

            def draw(self, renderer):
                self.draws += 1

        game = Game(backend=StubBackend())
        scene = RecordingScene()
        game.scenes.push(scene)
        game.run(max_frames=10)
        self.assertEqual(scene.updates, 10)
        self.assertEqual(scene.draws, 10)

    def test_scene_on_enter_called_once_when_pushed(self):
        class EnterScene(Scene):
            def __init__(self):
                super().__init__()
                self.enters = 0

            def on_enter(self):
                self.enters += 1

        game = Game(backend=NullBackend())
        scene = EnterScene()
        game.scenes.push(scene)
        self.assertEqual(scene.enters, 1)
        game.run(max_frames=3)
        self.assertEqual(scene.enters, 1)

    def test_scene_reads_input_through_game(self):
        class InputScene(Scene):
            def __init__(self):
                super().__init__()
                self.seen = False

            def update(self, dt):
                if self.game.input.is_key_pressed("space"):
                    self.seen = True
                self.game.close()

        backend = StubBackend([BackendEvent("key_down", {"key": "space", "repeat": False})])
        game = Game(backend=backend)
        scene = InputScene()
        scene.game = game
        game.scenes.push(scene)
        game.run(max_frames=10)
        self.assertTrue(scene.seen)

    def test_scene_handle_event_receives_events(self):
        class EventScene(Scene):
            def __init__(self):
                super().__init__()
                self.types = []

            def handle_event(self, event):
                self.types.append(event.type)

        backend = StubBackend(
            [
                BackendEvent("key_down", {"key": "a", "repeat": False}),
                BackendEvent("key_up", {"key": "a"}),
            ]
        )
        game = Game(backend=backend)
        scene = EventScene()
        game.scenes.push(scene)
        game.run(max_frames=1)
        self.assertEqual(scene.types, [EventType.KEY_DOWN, EventType.KEY_UP])

    def test_replace_during_run_switches_current_scene(self):
        class SwitcherScene(Scene):
            def __init__(self, other):
                super().__init__()
                self.other = other
                self.updates = 0
                self.exits = 0

            def on_exit(self):
                self.exits += 1

            def update(self, dt):
                self.updates += 1
                if self.updates == 2:
                    self.manager.replace(self.other)

        game = Game(backend=NullBackend())
        s1 = SwitcherScene(Scene())
        s2 = s1.other
        game.scenes.push(s1)
        game.run(max_frames=5)
        self.assertEqual(s1.updates, 2)
        self.assertEqual(s1.exits, 1)
        self.assertIs(game.scenes.current, s2)

    def test_pop_during_run_resumes_previous_scene(self):
        class PopperScene(Scene):
            def __init__(self):
                super().__init__()
                self.updates = 0
                self.exits = 0

            def on_exit(self):
                self.exits += 1

            def update(self, dt):
                self.updates += 1
                if self.updates == 1:
                    self.manager.pop()

        game = Game(backend=NullBackend())
        s1, s2 = Scene(), PopperScene()
        game.scenes.push(s1)
        game.scenes.push(s2)
        game.run(max_frames=5)
        self.assertEqual(s2.updates, 1)
        self.assertEqual(s2.exits, 1)
        self.assertIs(game.scenes.current, s1)

    def test_scene_with_sprite_and_label_draws_each_frame(self):
        backend = StubBackend(image_sizes={self._path: (16, 16)})
        game = Game(backend=backend)
        scene = Scene()
        scene.add(Sprite(self._path, backend=backend))
        scene.add(Label("HI", font=self._font_path, position=(5, 6), backend=backend))
        game.scenes.push(scene)
        game.run(max_frames=3)
        self.assertEqual(len(backend.renderers[0].texture_draws), 6)

    def test_no_scene_keeps_legacy_loop_behaviour(self):
        class HookGame(Game):
            def __init__(self, backend):
                super().__init__(backend=backend)
                self.updates = 0
                self.draws = 0

            def update(self, dt):
                self.updates += 1

            def draw(self):
                self.draws += 1

        game = HookGame(StubBackend())
        game.run(max_frames=4)
        self.assertEqual(game.updates, 4)
        self.assertEqual(game.draws, 4)


if __name__ == "__main__":
    unittest.main()