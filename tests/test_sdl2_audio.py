"""Integration tests for the real SDL_mixer audio backend.

These require ``pysdl2`` / ``pysdl2-dll`` but NOT a physical audio device:
the ``SDL_AUDIODRIVER=dummy`` environment variable makes SDL_mixer open a
software audio device, so the tests verify the real load/play/volume/state
pipeline without making any sound.  They are skipped when SDL2 is missing.
"""

import os
import tempfile
import time
import unittest

os.environ["SDL_AUDIODRIVER"] = "dummy"

from _audio_fixtures import write_wav

import pydex_ge
from pydex_ge.audio import Audio
from pydex_ge.backend.sdl2 import SDL2Backend
from pydex_ge.exceptions import BackendError

_SDL2_AVAILABLE = SDL2Backend().is_available()


def _can_open_audio() -> bool:
    backend = SDL2Backend()
    try:
        backend.open_audio()
        return True
    except BackendError:
        return False
    finally:
        backend.close_audio()


@unittest.skipUnless(_SDL2_AVAILABLE, "SDL2 backend (pysdl2/pysdl2-dll) not available")
@unittest.skipUnless(_can_open_audio(), "SDL_mixer could not open an audio device (dummy)")
class TestSDL2Audio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sound_path = write_wav(self.tmp.name, "jump.wav", seconds=0.2)
        self.music_path = write_wav(self.tmp.name, "theme.wav", seconds=0.2)
        self.backend = SDL2Backend()

    def tearDown(self):
        self.backend.quit()

    def test_open_close_audio_idempotent(self):
        self.backend.open_audio()
        self.assertTrue(self.backend._audio_open)
        self.backend.open_audio()
        self.backend.close_audio()
        self.assertFalse(self.backend._audio_open)
        self.backend.close_audio()

    def test_load_sound_and_play(self):
        sound = pydex_ge.Sound(self.sound_path, backend=self.backend)
        self.assertFalse(sound.playing)
        sound.play()
        time.sleep(0.02)
        self.assertTrue(sound.playing)
        sound.stop()
        self.assertFalse(sound.playing)
        sound.destroy()

    def test_sound_pause_resume(self):
        sound = pydex_ge.Sound(self.sound_path, backend=self.backend)
        sound.play()
        time.sleep(0.02)
        sound.pause()
        self.assertTrue(sound.paused)
        self.assertTrue(sound.playing)
        sound.resume()
        self.assertFalse(sound.paused)
        sound.stop()
        sound.destroy()

    def test_sound_volume(self):
        sound = pydex_ge.Sound(self.sound_path, backend=self.backend)
        sound.play()
        sound.volume = 0.5
        self.assertEqual(sound.volume, 0.5)
        sound.stop()
        sound.destroy()

    def test_load_music_and_play(self):
        music = pydex_ge.Music(self.music_path, backend=self.backend)
        self.assertFalse(music.playing)
        music.play(loop=True)
        self.assertTrue(music.playing)
        music.pause()
        self.assertTrue(music.paused)
        music.resume()
        self.assertFalse(music.paused)
        music.stop()
        self.assertFalse(music.playing)
        music.destroy()

    def test_music_volume(self):
        music = pydex_ge.Music(self.music_path, backend=self.backend)
        music.play()
        music.volume = 0.25
        self.assertEqual(music.volume, 0.25)
        music.stop()
        music.destroy()

    def test_backend_volumes(self):
        self.backend.open_audio()
        self.backend.set_master_volume(0.5)
        self.assertEqual(self.backend.master_volume(), 0.5)
        self.backend.set_sound_volume(0.4)
        self.assertEqual(self.backend.sound_volume(), 0.4)
        self.backend.set_music_volume(0.6)
        self.assertEqual(self.backend.music_volume(), 0.6)

    def test_backend_volume_validation(self):
        self.backend.open_audio()
        for method in (
            self.backend.set_master_volume,
            self.backend.set_sound_volume,
            self.backend.set_music_volume,
        ):
            for bad in (-0.1, 1.5, True, "x", None):
                with self.assertRaises(BackendError):
                    method(bad)

    def test_backend_load_missing_file(self):
        with self.assertRaises(BackendError):
            self.backend.load_sound("does_not_exist.wav")
        with self.assertRaises(BackendError):
            self.backend.load_music("does_not_exist.ogg")

    def test_backend_load_invalid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.wav")
            with open(bad, "wb") as handle:
                handle.write(b"this is not a wav file at all")
            with self.assertRaises(BackendError):
                self.backend.load_sound(bad)

    def test_multiple_sounds_overlap(self):
        a = pydex_ge.Sound(self.sound_path, backend=self.backend)
        b = pydex_ge.Sound(self.sound_path, backend=self.backend)
        a.play()
        b.play()
        time.sleep(0.02)
        self.assertTrue(a.playing)
        self.assertTrue(b.playing)
        a.stop()
        self.assertFalse(a.playing)
        self.assertTrue(b.playing)
        a.destroy()
        b.destroy()

    def test_audio_manager_real_backend(self):
        audio = Audio(backend=self.backend)
        sound = audio.play_sound(self.sound_path)
        music = audio.play_music(self.music_path)
        self.assertTrue(sound.playing)
        self.assertTrue(music.playing)
        audio.pause()
        self.assertTrue(sound.paused)
        self.assertTrue(music.paused)
        audio.resume()
        audio.stop()
        self.assertFalse(sound.playing)
        self.assertFalse(music.playing)
        audio.close()

    def test_game_style_usage(self):
        """Loading through the manager and cleaning up mirrors a game loop."""
        audio = Audio(backend=self.backend)
        audio.master_volume = 0.9
        audio.sound_volume = 0.8
        audio.music_volume = 0.7
        sound = audio.play_sound(self.sound_path, loop=True)
        music = audio.play_music(self.music_path, loop=True)
        time.sleep(0.02)
        self.assertTrue(sound.playing)
        self.assertTrue(music.playing)
        audio.clear()
        self.assertEqual(len(audio._sounds), 0)
        self.assertEqual(len(audio._musics), 0)
        audio.close()


if __name__ == "__main__":
    unittest.main()
