"""Tests for the SplashScreen: lifecycle, clipping, loading, and transitions."""

import os
import tempfile
import unittest
from unittest import mock

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubRenderer

from pydex_ge import (
    Assets,
    ConfigurationError,
    Event,
    EventType,
    Game,
    Image,
    Renderer,
    Scene,
    SceneManager,
    SplashScreen,
    Sprite,
)
from pydex_ge.backend.null import NullBackend
from pydex_ge.exceptions import BackendError
from pydex_ge.graphics.font import Font


def _font_bytes() -> bytes:
    return b"\x00\x01\x00\x00 fake ttf bytes"


class SplashTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._env = mock.patch.dict(os.environ, {"PYDEX_BACKEND": "null"})
        self._env.start()
        self.addCleanup(self._env.stop)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.img_path = write_fixture(self._tmp.name, "logo.bmp", bmp_bytes(64, 64))
        self.font_path = os.path.join(self._tmp.name, "font.ttf")
        with open(self.font_path, "wb") as handle:
            handle.write(_font_bytes())
        self.font = Font(self.font_path, 40, backend=NullBackend())

    def assets(self) -> Assets:
        return Assets(backend=NullBackend())

    def font18(self) -> Font:
        return Font(self.font_path, 18, backend=NullBackend())

    def renderer(self):
        return Renderer(StubRenderer())

    def stub(self, renderer):
        return renderer._renderer


class TestSplashDefaults(SplashTestBase):
    def test_defaults(self):
        splash = SplashScreen()
        self.assertEqual(splash.state, "idle")
        self.assertEqual(splash.progress, 0.0)
        self.assertIsNone(splash.logo)
        self.assertEqual(splash.width, 800)
        self.assertEqual(splash.height, 600)
        self.assertIsNone(splash._name_label)
        self.assertIsNotNone(splash._status_label)
        self.assertIsInstance(splash.assets, Assets)
        self.assertEqual(splash.status, "")

    def test_custom_dimensions(self):
        splash = SplashScreen(width=1024, height=768)
        self.assertEqual(splash.width, 1024)
        self.assertEqual(splash.height, 768)

    def test_custom_size_validation(self):
        for bad in (0, -1, True, 1.5, "big"):
            with self.assertRaises(ConfigurationError):
                SplashScreen(width=bad)
            with self.assertRaises(ConfigurationError):
                SplashScreen(height=bad)

    def test_logo_shape_validation(self):
        for shape in ("none", "circle", "rounded"):
            splash = SplashScreen(logo_shape=shape)
            self.assertEqual(splash._logo_shape, shape)
        with self.assertRaises(ConfigurationError):
            SplashScreen(logo_shape="star")

    def test_logo_validation(self):
        with self.assertRaises(ConfigurationError):
            SplashScreen(logo=123)
        with self.assertRaises(ConfigurationError):
            SplashScreen(logo="   ")

    def test_name_and_version_validation(self):
        for bad in (123, 4.5, True, b"name"):
            with self.assertRaises(ConfigurationError):
                SplashScreen(name=bad)
            with self.assertRaises(ConfigurationError):
                SplashScreen(version=bad)

    def test_loading_speed_validation(self):
        for bad in (0, -1, True, "fast"):
            with self.assertRaises(ConfigurationError):
                SplashScreen(loading_speed=bad)

    def test_min_duration_validation(self):
        for bad in (0, -1, True, "soon"):
            with self.assertRaises(ConfigurationError):
                SplashScreen(min_duration=bad)
        self.assertIsNone(SplashScreen(min_duration=None)._min_duration)
        self.assertEqual(SplashScreen(min_duration=2.0)._min_duration, 2.0)

    def test_loading_text_validation(self):
        with self.assertRaises(ConfigurationError):
            SplashScreen(loading_text=42)

    def test_assets_validation(self):
        with self.assertRaises(ConfigurationError):
            SplashScreen(assets="assets")
        with self.assertRaises(ConfigurationError):
            SplashScreen(assets=123)

    def test_next_scene_validation(self):
        for bad in ("menu", 42, []):
            with self.assertRaises(ConfigurationError):
                SplashScreen(next_scene=bad)
        self.assertIsNone(SplashScreen(next_scene=None)._next_scene)

    def test_loadables_validation(self):
        with self.assertRaises(ConfigurationError):
            SplashScreen(loadables=[("", "x.png")])
        with self.assertRaises(ConfigurationError):
            SplashScreen(loadables=[("image",)])
        with self.assertRaises(ConfigurationError):
            SplashScreen(loadables=[123])


class TestSplashStateMachine(SplashTestBase):
    def test_start_without_file_checking_goes_straight_to_loading(self):
        splash = SplashScreen(file_checking=False)
        splash.start()
        self.assertEqual(splash.state, "loading")

    def test_start_with_file_checking_goes_to_checking(self):
        splash = SplashScreen(file_checking=True)
        splash.start()
        self.assertEqual(splash.state, "checking")

    def test_on_enter_auto_starts(self):
        manager = SceneManager()
        splash = SplashScreen(file_checking=False)
        manager.push(splash)
        self.assertEqual(splash.state, "loading")

    def test_empty_loadables_complete_fast(self):
        splash = SplashScreen(file_checking=False)
        splash.start()
        self.assertEqual(splash.state, "loading")
        splash.update(0.1)
        self.assertEqual(splash.state, "starting")
        splash.update(0.5)
        self.assertEqual(splash.state, "done")
        self.assertEqual(splash.progress, 1.0)

    def test_phase_status_text(self):
        splash = SplashScreen(
            name="Game",
            name_font=self.font,
            file_checking=True,
            loadables=[("image", self.img_path)],
            assets=self.assets(),
            loading_text="Warming up...",
        )
        splash.start()
        self.assertEqual(splash.state, "checking")
        self.assertEqual(splash.status, "Checking...")
        self.assertEqual(splash._status_label.text, "Checking...")
        splash.update(0.6)
        self.assertEqual(splash.state, "loading")
        self.assertEqual(splash.status, "Warming up...")
        splash.update(1.1)
        self.assertEqual(splash.state, "starting")
        self.assertEqual(splash.status, "Starting...")
        splash.update(0.5)
        self.assertEqual(splash.state, "done")

    def test_progress_never_exceeds_one(self):
        splash = SplashScreen(
            loadables=[("image", self.img_path)] * 3,
            file_checking=False,
            loading_speed=1.0,
            assets=self.assets(),
            name_font=self.font,
        )
        splash.start()
        for _ in range(20):
            splash.update(2.0)
            self.assertLessEqual(splash.progress, 1.0)
            self.assertGreaterEqual(splash.progress, 0.0)

    def test_start_restarts(self):
        splash = SplashScreen(file_checking=False)
        splash.start()
        splash.update(1.0)
        splash.update(0.5)
        self.assertEqual(splash.state, "done")
        splash.start()
        self.assertEqual(splash.state, "loading")
        self.assertEqual(splash.progress, 0.0)


class TestSplashLogo(SplashTestBase):
    def test_logo_from_path(self):
        splash = SplashScreen(logo=self.img_path, file_checking=False, assets=self.assets())
        self.assertIsInstance(splash.logo, Sprite)
        self.assertEqual(splash.logo.width, 64)
        self.assertEqual(splash.logo.height, 64)

    def test_logo_from_image(self):
        image = Image(self.img_path, backend=NullBackend())
        splash = SplashScreen(logo=image, file_checking=False)
        self.assertIsInstance(splash.logo, Sprite)
        self.assertIs(splash.logo._image, image)

    def test_logo_from_sprite(self):
        sprite = Sprite(self.img_path, backend=NullBackend())
        splash = SplashScreen(logo=sprite, file_checking=False)
        self.assertIs(splash.logo, sprite)

    def test_logo_positioned_centered(self):
        splash = SplashScreen(
            logo=self.img_path,
            file_checking=False,
            assets=self.assets(),
            width=800,
            height=600,
        )
        self.assertEqual(splash._logo_w, 64)
        self.assertEqual(splash._logo_h, 64)
        self.assertEqual(splash._logo_x, 400 - 32)
        self.assertEqual(splash._logo_y, 180 - 32)

    def test_circle_clipping_draws_background_masks(self):
        splash = SplashScreen(
            logo=self.img_path,
            logo_shape="circle",
            file_checking=False,
            assets=self.assets(),
            background_color=(10, 20, 30),
        )
        renderer = self.renderer()
        splash.draw(renderer)
        stub = self.stub(renderer)
        mask_color = (10, 20, 30, 255)
        masks = [
            rect
            for rect in stub.rects
            if rect[4] == mask_color and rect[3] == 1
        ]
        self.assertTrue(masks, "circle clipping should emit background masks")
        for rect in masks:
            x, y, w, h = rect[:4]
            self.assertGreaterEqual(y, splash._logo_y)
            self.assertLess(y, splash._logo_y + splash._logo_h)
            self.assertGreaterEqual(x, splash._logo_x)
            self.assertLess(x, splash._logo_x + splash._logo_w)

    def test_rounded_clipping_draws_background_masks(self):
        splash = SplashScreen(
            logo=self.img_path,
            logo_shape="rounded",
            file_checking=False,
            assets=self.assets(),
            background_color=(10, 20, 30),
        )
        renderer = self.renderer()
        splash.draw(renderer)
        stub = self.stub(renderer)
        masks = [
            rect
            for rect in stub.rects
            if rect[4] == (10, 20, 30, 255) and rect[3] == 1
        ]
        self.assertTrue(masks)

    def test_no_clipping_without_shape(self):
        splash = SplashScreen(
            logo=self.img_path,
            logo_shape="none",
            file_checking=False,
            assets=self.assets(),
            background_color=(10, 20, 30),
            show_progress=False,
        )
        renderer = self.renderer()
        splash.draw(renderer)
        stub = self.stub(renderer)
        masks = [
            rect
            for rect in stub.rects
            if rect[4] == (10, 20, 30, 255) and rect[3] == 1
        ]
        self.assertEqual(masks, [])


class TestSplashText(SplashTestBase):
    def test_name_version_and_branding(self):
        splash = SplashScreen(
            name="My Game",
            name_font=self.font,
            version="1.0.0",
            name_color=(10, 200, 30),
            file_checking=False,
        )
        self.assertEqual(splash._name_label.text, "My Game")
        self.assertEqual(splash._version_label.text, "v1.0.0")
        self.assertEqual(splash._branding_label.text, "PYDEX 1.0.0")
        self.assertEqual(splash._name_label.color, (10, 200, 30, 255))

    def test_no_labels_when_no_text(self):
        splash = SplashScreen(file_checking=False)
        self.assertIsNone(splash._name_label)
        self.assertIsNone(splash._version_label)
        self.assertIsNone(splash._branding_label)
        self.assertIsNone(splash._status_label)

    def test_draw_renders_labels(self):
        splash = SplashScreen(
            name="My Game",
            name_font=self.font,
            version="1.0.0",
            file_checking=False,
        )
        renderer = self.renderer()
        splash.draw(renderer)
        self.assertTrue(self.stub(renderer).texture_draws)


class TestSplashFileChecking(SplashTestBase):
    def test_missing_file_raises_backend_error(self):
        missing = os.path.join(self._tmp.name, "missing.bmp")
        splash = SplashScreen(
            loadables=[("image", missing)],
            file_checking=True,
            assets=self.assets(),
            name_font=self.font,
        )
        with self.assertRaises(BackendError):
            splash.start()

    def test_ui_stays_generic_while_checking(self):
        missing = os.path.join(self._tmp.name, "secret_asset_name.bmp")
        splash = SplashScreen(
            loadables=[("image", missing)],
            file_checking=True,
            assets=self.assets(),
            name_font=self.font,
        )
        with self.assertRaises(BackendError):
            splash.start()
        self.assertEqual(splash.status, "Checking...")
        self.assertNotIn("secret_asset_name", splash.status)

    def test_missing_file_raised_during_loading_without_checking(self):
        missing = os.path.join(self._tmp.name, "missing.bmp")
        splash = SplashScreen(
            loadables=[("image", missing)],
            file_checking=False,
            loading_speed=1.0,
            assets=self.assets(),
            name_font=self.font,
        )
        splash.start()
        with self.assertRaises(BackendError):
            splash.update(1.1)

    def test_missing_logo_raises_at_construction(self):
        with self.assertRaises(BackendError):
            SplashScreen(logo=os.path.join(self._tmp.name, "nope.bmp"))


class TestSplashLoadables(SplashTestBase):
    def test_image_loadable_caches(self):
        assets = self.assets()
        splash = SplashScreen(
            loadables=[("image", self.img_path), ("image", self.img_path)],
            file_checking=False,
            loading_speed=10.0,
            assets=assets,
            name_font=self.font,
        )
        splash.start()
        splash.update(0.5)
        self.assertEqual(len(assets), 1)
        self.assertEqual(len(splash.loaded), 2)
        self.assertIs(splash.loaded[0], splash.loaded[1])
        self.assertIs(splash.loaded[0], assets.image(self.img_path))

    def test_font_loadable(self):
        assets = self.assets()
        splash = SplashScreen(
            loadables=[("font", self.font_path, 16)],
            file_checking=False,
            loading_speed=1.0,
            assets=assets,
            name_font=self.font,
        )
        splash.start()
        splash.update(1.1)
        self.assertEqual(len(splash.loaded), 1)
        self.assertIs(splash.loaded[0], assets.font(self.font_path, 16))

    def test_sprite_sheet_loadable(self):
        assets = self.assets()
        splash = SplashScreen(
            loadables=[("sprite_sheet", self.img_path, 16, 16)],
            file_checking=False,
            loading_speed=1.0,
            assets=assets,
            name_font=self.font,
        )
        splash.start()
        splash.update(1.1)
        self.assertEqual(len(splash.loaded), 1)
        self.assertIs(
            splash.loaded[0],
            assets.sprite_sheet(self.img_path, 16, 16),
        )
        self.assertIs(splash.loaded[0].image, assets.image(self.img_path))

    def test_callable_loadable_receives_assets(self):
        assets = self.assets()
        calls = []

        def loader(shared):
            calls.append(shared)
            return "loaded"

        splash = SplashScreen(
            loadables=[loader],
            file_checking=False,
            loading_speed=1.0,
            assets=assets,
            name_font=self.font,
        )
        splash.start()
        splash.update(1.1)
        self.assertEqual(calls, [assets])
        self.assertEqual(splash.loaded, ["loaded"])

    def test_callable_may_return_none(self):
        splash = SplashScreen(
            loadables=[lambda assets: None],
            file_checking=False,
            loading_speed=1.0,
            assets=self.assets(),
            name_font=self.font,
        )
        splash.start()
        splash.update(1.1)
        self.assertEqual(splash.loaded, [None])

    def test_unknown_kind_raises_during_load(self):
        splash = SplashScreen(
            loadables=[("mesh", "model.obj")],
            file_checking=False,
            loading_speed=1.0,
            assets=self.assets(),
            name_font=self.font,
        )
        splash.start()
        with self.assertRaises(ConfigurationError):
            splash.update(1.1)

    def test_register_loader_on_class(self):
        class MeshSplash(SplashScreen):
            pass

        def mesh_loader(assets, path):
            return f"mesh:{path}"

        MeshSplash.register_loader("mesh", mesh_loader)
        splash = MeshSplash(
            loadables=[("mesh", "model.obj")],
            file_checking=False,
            loading_speed=1.0,
            assets=self.assets(),
            name_font=self.font,
        )
        splash.start()
        splash.update(1.1)
        self.assertEqual(splash.loaded, ["mesh:model.obj"])

    def test_register_loader_on_instance(self):
        def custom_loader(assets, path, flag):
            return f"{flag}:{path}"

        SplashScreen.register_loader("custom_type", custom_loader)
        splash = SplashScreen(
            loadables=[("custom_type", "thing.bin", "ok")],
            file_checking=False,
            loading_speed=1.0,
            assets=self.assets(),
            name_font=self.font,
        )
        splash.start()
        splash.update(1.1)
        self.assertEqual(splash.loaded, ["ok:thing.bin"])

    def test_register_loader_validation(self):
        with self.assertRaises(ConfigurationError):
            SplashScreen.register_loader("", lambda assets, path: None)
        with self.assertRaises(ConfigurationError):
            SplashScreen.register_loader("kind", "not callable")


class TestSplashOwnership(SplashTestBase):
    def test_caller_assets_never_cleared(self):
        assets = self.assets()
        assets.image(self.img_path)
        splash = SplashScreen(
            loadables=[("image", self.img_path)],
            file_checking=False,
            loading_speed=1.0,
            assets=assets,
            name_font=self.font,
        )
        splash.start()
        splash.update(1.1)
        splash.on_exit()
        self.assertTrue(assets.contains(self.img_path))
        self.assertEqual(len(assets), 1)

    def test_owned_assets_cleared_on_exit(self):
        splash = SplashScreen(
            loadables=[("image", self.img_path)],
            file_checking=False,
            loading_speed=1.0,
            name_font=self.font,
        )
        splash.start()
        splash.update(1.1)
        self.assertTrue(splash.assets.contains(self.img_path))
        splash.on_exit()
        self.assertEqual(len(splash.assets), 0)
        self.assertFalse(splash.assets.contains(self.img_path))

    def test_shared_font_not_destroyed(self):
        splash = SplashScreen(
            name="Game",
            name_font=self.font,
            file_checking=False,
            assets=self.assets(),
        )
        splash.on_exit()
        self.assertEqual(self.font.measure("x")[1], 40)

    def test_path_font_destroyed_on_exit(self):
        splash = SplashScreen(
            name="Game",
            name_font=self.font_path,
            file_checking=False,
            assets=self.assets(),
        )
        owned = splash._name_font
        splash.on_exit()
        with self.assertRaises(RuntimeError):
            owned.measure("x")


class TestSplashTransition(SplashTestBase):
    class MainMenu(Scene):
        pass

    def test_transitions_to_scene_instance(self):
        menu = self.MainMenu()
        splash = SplashScreen(next_scene=menu, file_checking=False)
        manager = SceneManager()
        manager.push(splash)
        splash.update(0.1)
        splash.update(0.5)
        self.assertIs(manager.current, menu)
        self.assertEqual(len(manager), 1)

    def test_transitions_to_scene_class(self):
        splash = SplashScreen(next_scene=self.MainMenu, file_checking=False)
        manager = SceneManager()
        manager.push(splash)
        splash.update(0.1)
        splash.update(0.5)
        self.assertIsInstance(manager.current, self.MainMenu)

    def test_transitions_to_callable(self):
        calls = []
        def make_menu():
            calls.append(1)
            return self.MainMenu()
        splash = SplashScreen(next_scene=make_menu, file_checking=False)
        manager = SceneManager()
        manager.push(splash)
        splash.update(0.1)
        splash.update(0.5)
        self.assertEqual(calls, [1])
        self.assertIsInstance(manager.current, self.MainMenu)

    def test_no_transition_without_next_scene(self):
        splash = SplashScreen(file_checking=False)
        manager = SceneManager()
        manager.push(splash)
        splash.update(0.1)
        splash.update(0.5)
        self.assertEqual(splash.state, "done")
        self.assertIs(manager.current, splash)

    def test_no_transition_without_manager(self):
        splash = SplashScreen(next_scene=self.MainMenu, file_checking=False)
        splash.start()
        splash.update(1.0)
        splash.update(0.5)
        self.assertEqual(splash.state, "done")

    def test_min_duration_holds_splash(self):
        splash = SplashScreen(
            next_scene=self.MainMenu,
            file_checking=False,
            min_duration=3.0,
        )
        manager = SceneManager()
        manager.push(splash)
        splash.update(0.1)
        splash.update(0.5)
        self.assertEqual(splash.state, "done")
        self.assertIs(manager.current, splash)
        splash.update(1.0)
        self.assertIs(manager.current, splash)
        splash.update(2.0)
        self.assertIsInstance(manager.current, self.MainMenu)

    def test_transitioned_scene_cleaned_up(self):
        menu = self.MainMenu()
        splash = SplashScreen(
            next_scene=menu,
            file_checking=False,
            loadables=[("image", self.img_path)],
            loading_speed=1.0,
            name_font=self.font,
        )
        manager = SceneManager()
        manager.push(splash)
        splash.update(1.1)
        splash.update(0.5)
        self.assertIs(manager.current, menu)
        self.assertEqual(len(splash.assets), 0)


class TestSplashCancellation(SplashTestBase):
    def _open_game(self):
        game = Game(backend=NullBackend())
        game.window.open()
        return game

    def test_escape_closes_game_when_cancellable(self):
        game = self._open_game()
        splash = SplashScreen(game=game)
        self.assertFalse(game.window.closed)
        splash.handle_event(Event(EventType.KEY_DOWN, {"key": "escape"}))
        self.assertTrue(game.window.closed)

    def test_escape_ignored_when_not_cancellable(self):
        game = self._open_game()
        splash = SplashScreen(game=game, cancellable=False)
        splash.handle_event(Event(EventType.KEY_DOWN, {"key": "escape"}))
        self.assertFalse(game.window.closed)

    def test_escape_ignored_without_game(self):
        splash = SplashScreen()
        splash.handle_event(Event(EventType.KEY_DOWN, {"key": "escape"}))
        splash.handle_event(Event(EventType.KEY_DOWN, {"key": "e"}))

    def test_quit_event_closes_game(self):
        game = self._open_game()
        splash = SplashScreen(game=game)
        splash.handle_event(Event(EventType.QUIT))
        self.assertTrue(game.window.closed)

    def test_window_close_event_closes_game(self):
        game = self._open_game()
        splash = SplashScreen(game=game)
        splash.handle_event(Event(EventType.WINDOW_CLOSE))
        self.assertTrue(game.window.closed)

    def test_other_keys_do_not_cancel(self):
        game = self._open_game()
        splash = SplashScreen(game=game)
        splash.handle_event(Event(EventType.KEY_DOWN, {"key": "a"}))
        self.assertFalse(game.window.closed)


class TestSplashPublicApi(SplashTestBase):
    def test_exported_from_package(self):
        import pydex_ge
        import pydex_ge.loading

        self.assertIs(pydex_ge.SplashScreen, SplashScreen)
        self.assertIs(pydex_ge.loading.SplashScreen, SplashScreen)
        self.assertIn("SplashScreen", pydex_ge.__all__)


if __name__ == "__main__":
    unittest.main()
