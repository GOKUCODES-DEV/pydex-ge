"""Headless audio tests: Sound, Music, Audio manager, assets, and the NullBackend.

These never touch a real audio device; they run against the in-memory
``NullBackend`` and the ``StubBackend``.
"""

import os
import tempfile
import unittest

from _audio_fixtures import write_wav
from _stub_backend import StubBackend

import pydex_ge
from pydex_ge.audio import Audio
from pydex_ge.backend.null import NullBackend
from pydex_ge.exceptions import BackendError, ConfigurationError


class AudioSetupMixin:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sound_path = write_wav(self.tmp.name, "jump.wav")
        self.music_path = write_wav(self.tmp.name, "theme.wav")


class TestSoundNull(AudioSetupMixin, unittest.TestCase):
    def test_load(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        self.assertEqual(sound.path, os.path.abspath(self.sound_path))
        self.assertFalse(sound.playing)
        self.assertFalse(sound.paused)
        sound.destroy()
        backend.quit()

    def test_invalid_path_raises_backend_error(self):
        backend = NullBackend()
        with self.assertRaises(BackendError):
            pydex_ge.Sound(os.path.join(self.tmp.name, "missing.wav"), backend=backend)
        backend.quit()

    def test_empty_path_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            pydex_ge.Sound("   ", backend=NullBackend())

    def test_play_stop(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        sound.play()
        self.assertTrue(sound.playing)
        sound.stop()
        self.assertFalse(sound.playing)
        self.assertFalse(sound.paused)
        sound.destroy()
        backend.quit()

    def test_pause_resume(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        sound.play()
        sound.pause()
        self.assertTrue(sound.paused)
        self.assertTrue(sound.playing)
        sound.resume()
        self.assertFalse(sound.paused)
        sound.destroy()
        backend.quit()

    def test_pause_without_play_is_noop(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        sound.pause()
        self.assertFalse(sound.paused)
        sound.resume()
        self.assertFalse(sound.paused)
        sound.destroy()
        backend.quit()

    def test_loop(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        sound.play(loop=True)
        self.assertTrue(sound.playing)
        sound.destroy()
        backend.quit()

    def test_volume(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        self.assertEqual(sound.volume, 1.0)
        sound.volume = 0.5
        self.assertEqual(sound.volume, 0.5)
        sound.volume = 0.0
        self.assertEqual(sound.volume, 0.0)
        sound.volume = 1.0
        self.assertEqual(sound.volume, 1.0)
        for bad in (-0.1, 1.5, True, "loud", None):
            with self.assertRaises(ConfigurationError):
                sound.volume = bad
        sound.destroy()
        backend.quit()

    def test_destroy_idempotent(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        sound.destroy()
        sound.destroy()

    def test_unusable_after_destroy(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        sound.destroy()
        with self.assertRaises(RuntimeError):
            sound.play()

    def test_repeated_load_is_independent(self):
        # Two Sound objects (even from the same path) are independent so they
        # can overlap; the Audio manager provides path-level caching instead.
        backend = NullBackend()
        first = pydex_ge.Sound(self.sound_path, backend=backend)
        second = pydex_ge.Sound(self.sound_path, backend=backend)
        self.assertIsNot(first._sound, second._sound)
        first.destroy()
        second.destroy()
        backend.quit()

    def test_multiple_sounds_at_once(self):
        backend = NullBackend()
        a = pydex_ge.Sound(self.sound_path, backend=backend)
        b = pydex_ge.Sound(self.sound_path, backend=backend)
        a.play()
        b.play()
        self.assertTrue(a.playing)
        self.assertTrue(b.playing)
        a.stop()
        self.assertFalse(a.playing)
        self.assertTrue(b.playing)
        a.destroy()
        b.destroy()
        backend.quit()


class TestMusicNull(AudioSetupMixin, unittest.TestCase):
    def test_load(self):
        backend = NullBackend()
        music = pydex_ge.Music(self.music_path, backend=backend)
        self.assertEqual(music.path, os.path.abspath(self.music_path))
        self.assertFalse(music.playing)
        self.assertFalse(music.paused)
        music.destroy()
        backend.quit()

    def test_invalid_path_raises_backend_error(self):
        backend = NullBackend()
        with self.assertRaises(BackendError):
            pydex_ge.Music(os.path.join(self.tmp.name, "missing.ogg"), backend=backend)
        backend.quit()

    def test_empty_path_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            pydex_ge.Music("   ", backend=NullBackend())

    def test_play_stop(self):
        backend = NullBackend()
        music = pydex_ge.Music(self.music_path, backend=backend)
        music.play()
        self.assertTrue(music.playing)
        music.stop()
        self.assertFalse(music.playing)
        self.assertFalse(music.paused)
        music.destroy()
        backend.quit()

    def test_pause_resume(self):
        backend = NullBackend()
        music = pydex_ge.Music(self.music_path, backend=backend)
        music.play()
        music.pause()
        self.assertTrue(music.paused)
        music.resume()
        self.assertFalse(music.paused)
        music.destroy()
        backend.quit()

    def test_loop_defaults_on(self):
        backend = NullBackend()
        music = pydex_ge.Music(self.music_path, backend=backend)
        music.play()
        self.assertTrue(music.playing)
        music.destroy()
        backend.quit()

    def test_volume(self):
        backend = NullBackend()
        music = pydex_ge.Music(self.music_path, backend=backend)
        self.assertEqual(music.volume, 1.0)
        music.volume = 0.3
        self.assertEqual(music.volume, 0.3)
        for bad in (-0.1, 2.0, "music", True):
            with self.assertRaises(ConfigurationError):
                music.volume = bad
        music.destroy()
        backend.quit()

    def test_destroy_idempotent(self):
        backend = NullBackend()
        music = pydex_ge.Music(self.music_path, backend=backend)
        music.destroy()
        music.destroy()

    def test_unusable_after_destroy(self):
        backend = NullBackend()
        music = pydex_ge.Music(self.music_path, backend=backend)
        music.destroy()
        with self.assertRaises(RuntimeError):
            music.play()

    def test_repeated_load_is_independent(self):
        backend = NullBackend()
        first = pydex_ge.Music(self.music_path, backend=backend)
        second = pydex_ge.Music(self.music_path, backend=backend)
        self.assertIsNot(first._music, second._music)
        first.destroy()
        second.destroy()
        backend.quit()


class TestAudioManager(AudioSetupMixin, unittest.TestCase):
    def test_volumes(self):
        audio = Audio(backend=NullBackend())
        self.assertEqual(audio.master_volume, 1.0)
        self.assertEqual(audio.sound_volume, 1.0)
        self.assertEqual(audio.music_volume, 1.0)
        audio.master_volume = 0.4
        audio.sound_volume = 0.6
        audio.music_volume = 0.8
        self.assertEqual(audio.master_volume, 0.4)
        self.assertEqual(audio.sound_volume, 0.6)
        self.assertEqual(audio.music_volume, 0.8)
        for bad in (-0.1, 1.5, True, "x"):
            with self.assertRaises(ConfigurationError):
                audio.master_volume = bad
        audio.close()

    def test_load_caching(self):
        audio = Audio(backend=NullBackend())
        s1 = audio.load_sound(self.sound_path)
        s2 = audio.load_sound(self.sound_path)
        self.assertIs(s1, s2)
        m1 = audio.load_music(self.music_path)
        m2 = audio.load_music(self.music_path)
        self.assertIs(m1, m2)
        audio.clear()
        self.assertEqual(len(audio._sounds), 0)
        self.assertEqual(len(audio._musics), 0)
        audio.close()

    def test_play_sound_play_music(self):
        audio = Audio(backend=NullBackend())
        sound = audio.play_sound(self.sound_path)
        self.assertTrue(sound.playing)
        music = audio.play_music(self.music_path, loop=True)
        self.assertTrue(music.playing)
        audio.stop_sounds()
        self.assertFalse(sound.playing)
        self.assertTrue(music.playing)
        audio.stop_music()
        self.assertFalse(music.playing)
        audio.close()

    def test_global_pause_resume(self):
        audio = Audio(backend=NullBackend())
        sound = audio.play_sound(self.sound_path)
        music = audio.play_music(self.music_path)
        audio.pause()
        self.assertTrue(sound.paused)
        self.assertTrue(music.paused)
        audio.resume()
        self.assertFalse(sound.paused)
        self.assertFalse(music.paused)
        audio.close()

    def test_stop(self):
        audio = Audio(backend=NullBackend())
        sound = audio.play_sound(self.sound_path)
        music = audio.play_music(self.music_path)
        audio.stop()
        self.assertFalse(sound.playing)
        self.assertFalse(music.playing)
        audio.close()

    def test_close_releases_backend_audio(self):
        backend = NullBackend()
        audio = Audio(backend=backend)
        audio.play_sound(self.sound_path)
        audio.play_music(self.music_path)
        audio.close()
        self.assertFalse(backend._audio_open)
        self.assertEqual(len(backend._sounds), 0)
        self.assertEqual(len(backend._musics), 0)

    def test_close_is_idempotent(self):
        audio = Audio(backend=NullBackend())
        audio.close()
        audio.close()
        audio.destroy()
        audio.destroy()

    def test_manager_uses_default_backend(self):
        # Default (SDL2) backend should at least construct without crashing.
        audio = Audio()
        audio.close()


class TestAudioAssets(AudioSetupMixin, unittest.TestCase):
    def test_relative_path(self):
        original = os.getcwd()
        backend = NullBackend()
        try:
            os.chdir(self.tmp.name)
            sound = pydex_ge.Sound("jump.wav", backend=backend)
            self.assertEqual(sound.path, os.path.abspath(self.sound_path))
            sound.destroy()
        finally:
            os.chdir(original)
        backend.quit()

    def test_absolute_path(self):
        backend = NullBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        self.assertEqual(sound.path, os.path.abspath(self.sound_path))
        sound.destroy()
        backend.quit()

    def test_missing_file(self):
        backend = NullBackend()
        with self.assertRaises(BackendError):
            pydex_ge.Sound(os.path.join(self.tmp.name, "nope.wav"), backend=backend)
        with self.assertRaises(BackendError):
            pydex_ge.Music(os.path.join(self.tmp.name, "nope.ogg"), backend=backend)
        backend.quit()

    def test_manager_caching_by_path(self):
        audio = Audio(backend=NullBackend())
        a = audio.load_sound(self.sound_path)
        b = audio.load_sound(self.sound_path)
        self.assertIs(a, b)
        audio.close()

    def test_manager_cleanup(self):
        audio = Audio(backend=NullBackend())
        audio.load_sound(self.sound_path)
        audio.load_music(self.music_path)
        audio.clear()
        self.assertEqual(len(audio._sounds), 0)
        self.assertEqual(len(audio._musics), 0)
        audio.close()


class TestNullBackendAudio(unittest.TestCase):
    """The entire audio API works against NullBackend (headless)."""

    def test_open_close_audio_idempotent(self):
        backend = NullBackend()
        backend.open_audio()
        self.assertTrue(backend._audio_open)
        backend.open_audio()
        backend.close_audio()
        self.assertFalse(backend._audio_open)
        backend.close_audio()
        backend.quit()

    def test_volume_validation(self):
        backend = NullBackend()
        for method in (backend.set_master_volume, backend.set_sound_volume, backend.set_music_volume):
            for bad in (-0.1, 1.5, True, "x", None):
                with self.assertRaises(BackendError):
                    method(bad)
        backend.quit()

    def test_global_controls_via_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_wav(tmp, "s.wav")
            backend = NullBackend()
            sound = backend.load_sound(path)
            music = backend.load_music(path)
            sound.play()
            music.play()
            backend.pause_all()
            self.assertTrue(sound.paused)
            self.assertTrue(music.paused)
            backend.resume_all()
            self.assertFalse(sound.paused)
            self.assertFalse(music.paused)
            backend.stop_all()
            self.assertFalse(sound.playing)
            self.assertFalse(music.playing)
            backend.quit()


class TestAudioWithStubBackend(AudioSetupMixin, unittest.TestCase):
    def test_full_audio_api_with_stub(self):
        backend = StubBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        sound.play(loop=True)
        self.assertTrue(sound.playing)
        sound.pause()
        self.assertTrue(sound.paused)
        sound.resume()
        sound.stop()
        sound.volume = 0.25
        self.assertEqual(sound.volume, 0.25)
        sound.destroy()
        music = pydex_ge.Music(self.music_path, backend=backend)
        music.play(loop=False)
        self.assertTrue(music.playing)
        music.pause()
        self.assertTrue(music.paused)
        music.resume()
        music.stop()
        music.destroy()
        audio = Audio(backend=backend)
        audio.close()
        backend.quit()

    def test_destroyed_sound_removed_from_backend_cache(self):
        backend = StubBackend()
        sound = pydex_ge.Sound(self.sound_path, backend=backend)
        self.assertIn(sound._sound, backend._sounds)
        sound.destroy()
        self.assertNotIn(sound._sound, backend._sounds)
        backend.quit()


if __name__ == "__main__":
    unittest.main()
