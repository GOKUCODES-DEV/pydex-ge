"""Integration tests against the real SDL2 backend.

These require a working display and the ``pysdl2`` / ``pysdl2-dll``
packages.  They are skipped automatically when SDL2 is unavailable.
"""

import ctypes
import os
import tempfile
import unittest

from _image_fixtures import bmp_bytes, png_bytes, write_fixture

from pydex_ge import Game, Label, Sprite
from pydex_ge.backend.sdl2 import SDL2Backend, SDL2Renderer, SDL2Window
from pydex_ge.exceptions import BackendError

_SDL2_AVAILABLE = SDL2Backend().is_available()

_SYSTEM_FONT = None
for _candidate in (
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
):
    if os.path.isfile(_candidate):
        _SYSTEM_FONT = _candidate
        break


@unittest.skipUnless(_SDL2_AVAILABLE, "SDL2 backend (pysdl2/pysdl2-dll) not available")
class TestSDL2Backend(unittest.TestCase):
    def test_init_and_quit_are_idempotent(self):
        backend = SDL2Backend()
        backend.init()
        backend.quit()
        backend.quit()
        backend.init()
        backend.quit()

    def test_window_open_close_reopen(self):
        backend = SDL2Backend()
        window = backend.create_window("test", 320, 240)
        self.assertIsInstance(window, SDL2Window)
        self.assertFalse(window.closed)
        window.close()
        self.assertTrue(window.closed)
        window.close()  # idempotent
        backend.quit()
        backend.quit()

    def test_renderer_create_clear_present_destroy(self):
        backend = SDL2Backend()
        window = backend.create_window("test", 320, 240)
        renderer = backend.create_renderer(window)
        self.assertIsInstance(renderer, SDL2Renderer)
        renderer.clear(20, 20, 25, 255)
        renderer.present()
        renderer.destroy()
        renderer.destroy()  # idempotent
        window.close()
        backend.quit()

    def test_renderer_rejects_wrong_window_type(self):
        backend = SDL2Backend()
        from pydex_ge.backend.null import NullWindow

        with self.assertRaises(BackendError):
            backend.create_renderer(NullWindow())
        backend.quit()

    def test_renderer_drawing_primitives(self):
        backend = SDL2Backend()
        window = backend.create_window("test", 320, 240)
        renderer = backend.create_renderer(window)
        renderer.clear(10, 10, 10, 255)
        renderer.draw_pixel(10, 10, (255, 255, 255, 255))
        renderer.draw_line(0, 0, 50, 50, (255, 255, 255, 255))
        renderer.draw_rect(20, 20, 30, 30, (255, 0, 0, 255))
        renderer.draw_rect(20, 20, 30, 30, (255, 0, 0, 255), filled=False)
        renderer.draw_circle(80, 80, 20, (0, 255, 0, 255))
        renderer.draw_circle(80, 80, 20, (0, 255, 0, 255), filled=False)
        renderer.present()
        renderer.destroy()
        window.close()
        backend.quit()

    def test_game_run_with_sdl2_window(self):
        game = Game("SDL2 game", 320, 240, backend=SDL2Backend())
        game.background = (20, 20, 25)
        game.run(max_frames=10)
        self.assertTrue(game.window.closed)

    def test_load_image_dimensions(self):
        backend = SDL2Backend()
        with tempfile.TemporaryDirectory() as directory:
            image = backend.load_image(
                write_fixture(directory, "img.png", png_bytes(40, 30))
            )
            self.assertEqual((image.width, image.height), (40, 30))
            image.destroy()
            image = backend.load_image(
                write_fixture(directory, "img.bmp", bmp_bytes(16, 8))
            )
            self.assertEqual((image.width, image.height), (16, 8))
            image.destroy()
        backend.quit()

    def test_load_image_missing_file(self):
        backend = SDL2Backend()
        with self.assertRaises(BackendError):
            backend.load_image("does_not_exist.png")
        backend.quit()

    def test_texture_from_pixels_drawn_and_destroyed(self):
        backend = SDL2Backend()
        window = backend.create_window("test", 320, 240)
        renderer = backend.create_renderer(window)
        texture = renderer.create_texture_from_pixels(8, 8, bytes(8 * 8 * 4))
        self.assertEqual((texture.width, texture.height), (8, 8))
        renderer.clear(20, 20, 25, 255)
        renderer.draw_texture(texture, None, (40, 40, 80, 80), 255)
        renderer.present()
        renderer.destroy_texture(texture)
        texture.destroy()  # idempotent
        renderer.destroy()
        window.close()
        backend.quit()

    def test_texture_from_image_drawn_with_region(self):
        backend = SDL2Backend()
        window = backend.create_window("test", 320, 240)
        renderer = backend.create_renderer(window)
        with tempfile.TemporaryDirectory() as directory:
            image = backend.load_image(
                write_fixture(directory, "tile.bmp", bmp_bytes(16, 16))
            )
            texture = renderer.create_texture_from_image(image)
            renderer.draw_texture(texture, (4, 4, 8, 8), (10, 10, 16, 16), 128)
            renderer.present()
            renderer.destroy_texture(texture)
            image.destroy()
        renderer.destroy()
        window.close()
        backend.quit()

    def test_game_draws_pixel_sprite(self):
        class SpriteGame(Game):
            def __init__(self):
                super().__init__("sprite", 320, 240, backend=SDL2Backend())
                self.sprite = Sprite.from_pixels(8, 8, bytes(8 * 8 * 4))
                self.sprite.position = (50, 60)

            def draw(self):
                self.renderer.draw_sprite(self.sprite)

        game = SpriteGame()
        game.background = (20, 20, 25)
        game.run(max_frames=5)
        self.assertTrue(game.window.closed)

    @unittest.skipUnless(_SYSTEM_FONT, "no system TrueType font found")
    def test_load_font_and_measure(self):
        backend = SDL2Backend()
        font = backend.load_font(_SYSTEM_FONT, 24)
        self.assertEqual(font.size, 24)
        width, height = font.measure_text("Hello PYDEX")
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        font.destroy()
        backend.quit()

    @unittest.skipUnless(_SYSTEM_FONT, "no system TrueType font found")
    def test_load_font_missing_file(self):
        backend = SDL2Backend()
        with self.assertRaises(BackendError):
            backend.load_font("does_not_exist.ttf", 24)
        backend.quit()

    @unittest.skipUnless(_SYSTEM_FONT, "no system TrueType font found")
    def test_font_render_draw(self):
        backend = SDL2Backend()
        window = backend.create_window("text", 320, 240)
        renderer = backend.create_renderer(window)
        font = backend.load_font(_SYSTEM_FONT, 24)
        image = font.render_text("Hello PYDEX", (255, 255, 255, 255))
        texture = renderer.create_texture_from_image(image)
        renderer.clear(20, 20, 25, 255)
        renderer.draw_texture(texture, None, (10, 10, texture.width, texture.height), 255)
        renderer.present()
        renderer.destroy_texture(texture)
        image.destroy()
        font.destroy()
        renderer.destroy()
        window.close()
        backend.quit()

    @unittest.skipUnless(_SYSTEM_FONT, "no system TrueType font found")
    def test_mouse_position(self):
        backend = SDL2Backend()
        x, y = backend.mouse_position()
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        backend.quit()

    @unittest.skipUnless(_SYSTEM_FONT, "no system TrueType font found")
    def test_game_draws_label(self):
        class TextGame(Game):
            def __init__(self):
                super().__init__("text", 320, 240, backend=SDL2Backend())
                self.label = Label("Hello PYDEX", font=_SYSTEM_FONT, position=(20, 20))

            def draw(self):
                self.renderer.draw_label(self.label)

        game = TextGame()
        game.background = (20, 20, 25)
        game.run(max_frames=5)
        self.assertTrue(game.window.closed)

    @unittest.skipUnless(_SYSTEM_FONT, "no system TrueType font found")
    def test_synthetic_key_press_changes_label(self):
        """Push a real SDL key event; the game's input must see it."""

        import sdl2

        class KeyGame(Game):
            def __init__(self):
                super().__init__("keys", 320, 240, backend=SDL2Backend())
                self.label = Label("Press E", font=_SYSTEM_FONT, position=(20, 20))
                self.pressed = False

            def update(self, dt):
                if self.input.is_key_pressed("e") and not self.pressed:
                    self.pressed = True
                    self.label.text = "E was pressed!"

            def draw(self):
                self.renderer.draw_label(self.label)

        game = KeyGame()
        game.window.open()
        # Push a real SDL_KEYDOWN event with the E scancode.
        event = sdl2.SDL_Event()
        event.type = sdl2.SDL_KEYDOWN
        event.key.keysym.scancode = sdl2.SDL_SCANCODE_E
        event.key.keysym.sym = sdl2.SDLK_e
        event.key.state = sdl2.SDL_PRESSED
        event.key.repeat = 0
        sdl2.SDL_PushEvent(ctypes.byref(event))
        game.run(max_frames=10)
        self.assertTrue(game.pressed)
        self.assertEqual(game.label.text, "E was pressed!")
        self.assertTrue(game.window.closed)


if __name__ == "__main__":
    unittest.main()