"""The :class:`Sound` object: a reusable sound effect.

Sound effects can overlap (several playing at once).  A :class:`Sound` holds
the decoded clip; ``play()`` starts it on a free mixer channel.

Supported formats come from SDL_mixer's chunk decoders (at minimum WAV;
OGG/MP3 are available in the bundled SDL_mixer build).  A missing or invalid
file raises a clear :class:`~pydex_ge.exceptions.BackendError`.
"""

from __future__ import annotations

import os

from ..backend import select_backend
from ..backend.base import Backend, BackendSound
from ..check import _caller_info
from ..exceptions import ConfigurationError, MissingAssetError


class Sound:
    """A loaded sound-effect clip.

    Parameters
    ----------
    path:
        Filesystem path to a sound file (WAV, etc.).  Relative paths resolve
        against the process working directory.
    backend:
        Backend used to load and play the sound.  Defaults to SDL2 (or the
        ``PYDEX_BACKEND`` environment variable).
    """

    def __init__(self, path: str, *, backend: Backend | None = None) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ConfigurationError("Sound path must be a non-empty string.")
        self.path = os.path.abspath(path)
        self._backend = backend if backend is not None else select_backend()
        try:
            self._sound: BackendSound = self._backend.load_sound(self.path)
        except MissingAssetError as exc:
            if exc.requested_by is None:
                exc.requested_by = _caller_info()
            raise
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed:
            raise RuntimeError("Cannot use a sound after it has been destroyed.")

    def play(self, *, loop: bool = False) -> None:
        """Start playing the sound (restarting it if already playing).

        Parameters
        ----------
        loop:
            When ``True`` the sound repeats forever.
        """
        self._check()
        self._sound.play(loop=loop)

    def stop(self) -> None:
        """Stop playback and reset the sound to the beginning."""
        self._check()
        self._sound.stop()

    def pause(self) -> None:
        """Pause playback, keeping the current position."""
        self._check()
        self._sound.pause()

    def resume(self) -> None:
        """Resume playback from a paused position."""
        self._check()
        self._sound.resume()

    @property
    def playing(self) -> bool:
        """True while the sound is playing (paused counts as playing)."""
        self._check()
        return self._sound.playing

    @property
    def paused(self) -> bool:
        """True while the sound is paused."""
        self._check()
        return self._sound.paused

    @property
    def volume(self) -> float:
        """This sound's volume in the ``0.0-1.0`` range (default ``1.0``)."""
        self._check()
        return self._sound.volume

    @volume.setter
    def volume(self, value: object) -> None:
        self._check()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError("Sound volume must be a number between 0.0 and 1.0.")
        if not 0.0 <= float(value) <= 1.0:
            raise ConfigurationError("Sound volume must be between 0.0 and 1.0.")
        self._sound.set_volume(float(value))

    def destroy(self) -> None:
        """Free the sound.  Idempotent."""
        if self._destroyed:
            return
        self._sound.destroy()
        self._destroyed = True


__all__ = ["Sound"]
