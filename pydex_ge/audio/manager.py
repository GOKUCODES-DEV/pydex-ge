"""The :class:`Audio` manager: convenient control over all audio.

The manager bundles the three volume levels (master, sound, music), cached
loading of :class:`~pydex_ge.audio.sound.Sound` and
:class:`~pydex_ge.audio.music.Music` objects, global pause/resume/stop, and
one-call cleanup.
"""

from __future__ import annotations

import os

from ..backend import select_backend
from ..backend.base import Backend, BackendMusic, BackendSound
from ..exceptions import ConfigurationError
from .music import Music
from .sound import Sound


class Audio:
    """A convenient audio manager.

    Parameters
    ----------
    backend:
        Backend used for all audio.  Defaults to SDL2 (or the
        ``PYDEX_BACKEND`` environment variable).  The backend's audio
        subsystem is opened when the manager is created.
    """

    def __init__(self, *, backend: Backend | None = None) -> None:
        self._backend = backend if backend is not None else select_backend()
        self._backend.open_audio()
        self._sounds: dict[str, Sound] = {}
        self._musics: dict[str, Music] = {}

    # -- volume -----------------------------------------------------------

    @property
    def master_volume(self) -> float:
        """Master volume in the ``0.0-1.0`` range (default ``1.0``)."""
        return self._backend.master_volume()

    @master_volume.setter
    def master_volume(self, value: object) -> None:
        self._validate(value, "master")
        self._backend.set_master_volume(float(value))

    @property
    def sound_volume(self) -> float:
        """Global sound-effect volume in the ``0.0-1.0`` range (default ``1.0``)."""
        return self._backend.sound_volume()

    @sound_volume.setter
    def sound_volume(self, value: object) -> None:
        self._validate(value, "sound")
        self._backend.set_sound_volume(float(value))

    @property
    def music_volume(self) -> float:
        """Global music volume in the ``0.0-1.0`` range (default ``1.0``)."""
        return self._backend.music_volume()

    @music_volume.setter
    def music_volume(self, value: object) -> None:
        self._validate(value, "music")
        self._backend.set_music_volume(float(value))

    @staticmethod
    def _validate(value: object, which: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(
                f"{which} volume must be a number between 0.0 and 1.0."
            )
        if not 0.0 <= float(value) <= 1.0:
            raise ConfigurationError(f"{which} volume must be between 0.0 and 1.0.")

    # -- loading ----------------------------------------------------------

    def load_sound(self, path: str) -> Sound:
        """Load a sound once and return the cached :class:`Sound` afterwards."""
        if not isinstance(path, str) or not path.strip():
            raise ConfigurationError("Sound path must be a non-empty string.")
        key = os.path.normcase(os.path.abspath(path))
        cached = self._sounds.get(key)
        if cached is None:
            cached = Sound(key, backend=self._backend)
            self._sounds[key] = cached
        return cached

    def load_music(self, path: str) -> Music:
        """Load a track once and return the cached :class:`Music` afterwards."""
        if not isinstance(path, str) or not path.strip():
            raise ConfigurationError("Music path must be a non-empty string.")
        key = os.path.normcase(os.path.abspath(path))
        cached = self._musics.get(key)
        if cached is None:
            cached = Music(key, backend=self._backend)
            self._musics[key] = cached
        return cached

    def play_sound(self, path: str, *, loop: bool = False) -> Sound:
        """Load (cached) and play a sound, returning it."""
        sound = self.load_sound(path)
        sound.play(loop=loop)
        return sound

    def play_music(self, path: str, *, loop: bool = True) -> Music:
        """Load (cached) and play a track, returning it."""
        music = self.load_music(path)
        music.play(loop=loop)
        return music

    # -- control ----------------------------------------------------------

    def stop_sounds(self) -> None:
        """Stop every sound currently playing."""
        for sound in self._sounds.values():
            if not sound._destroyed:
                sound.stop()

    def stop_music(self) -> None:
        """Stop the currently playing music track."""
        for music in self._musics.values():
            if not music._destroyed:
                music.stop()

    def stop(self) -> None:
        """Stop every sound and music track."""
        self._backend.stop_all()

    def pause(self) -> None:
        """Pause every currently playing sound and music track."""
        self._backend.pause_all()

    def resume(self) -> None:
        """Resume everything paused by :meth:`pause`."""
        self._backend.resume_all()

    # -- cleanup ----------------------------------------------------------

    def clear(self) -> None:
        """Destroy every cached sound and track and empty the caches."""
        for sound in self._sounds.values():
            sound.destroy()
        self._sounds.clear()
        for music in self._musics.values():
            music.destroy()
        self._musics.clear()

    def close(self) -> None:
        """Stop all audio, free cached resources, and shut the audio subsystem down.

        Idempotent.
        """
        if getattr(self, "_closed", False):
            return
        self.clear()
        self._backend.close_audio()
        self._closed = True

    destroy = close


__all__ = ["Audio", "BackendMusic", "BackendSound"]
