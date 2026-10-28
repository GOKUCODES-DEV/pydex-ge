"""The :class:`Music` object: a music track.

Only one music track plays at a time; starting a new track replaces the one
currently playing.  Pause/resume/stop operate on that shared music channel.

Supported formats come from SDL_mixer's music decoders (at minimum WAV; OGG
and MP3 are available in the bundled SDL_mixer build).  A missing or invalid
file raises a clear :class:`~pydex_ge.exceptions.BackendError`.
"""

from __future__ import annotations

import os

from ..backend import select_backend
from ..backend.base import Backend, BackendMusic
from ..check import _caller_info
from ..exceptions import ConfigurationError, MissingAssetError


class Music:
    """A loaded music track.

    Parameters
    ----------
    path:
        Filesystem path to a music file (WAV/OGG/MP3).  Relative paths
        resolve against the process working directory.
    backend:
        Backend used to load and play the track.  Defaults to SDL2 (or the
        ``PYDEX_BACKEND`` environment variable).
    """

    def __init__(self, path: str, *, backend: Backend | None = None) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ConfigurationError("Music path must be a non-empty string.")
        self.path = os.path.abspath(path)
        self._backend = backend if backend is not None else select_backend()
        try:
            self._music: BackendMusic = self._backend.load_music(self.path)
        except MissingAssetError as exc:
            if exc.requested_by is None:
                exc.requested_by = _caller_info()
            raise
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed:
            raise RuntimeError("Cannot use music after it has been destroyed.")

    def play(self, *, loop: bool = True) -> None:
        """Start playing the track, replacing whatever music was playing.

        Parameters
        ----------
        loop:
            When ``True`` (the default) the track repeats forever.
        """
        self._check()
        self._music.play(loop=loop)

    def stop(self) -> None:
        """Stop playback and reset the track to the beginning."""
        self._check()
        self._music.stop()

    def pause(self) -> None:
        """Pause playback, keeping the current position."""
        self._check()
        self._music.pause()

    def resume(self) -> None:
        """Resume playback from a paused position."""
        self._check()
        self._music.resume()

    @property
    def playing(self) -> bool:
        """True while the track is playing (paused counts as playing)."""
        self._check()
        return self._music.playing

    @property
    def paused(self) -> bool:
        """True while the track is paused."""
        self._check()
        return self._music.paused

    @property
    def volume(self) -> float:
        """This track's volume in the ``0.0-1.0`` range (default ``1.0``)."""
        self._check()
        return self._music.volume

    @volume.setter
    def volume(self, value: object) -> None:
        self._check()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError("Music volume must be a number between 0.0 and 1.0.")
        if not 0.0 <= float(value) <= 1.0:
            raise ConfigurationError("Music volume must be between 0.0 and 1.0.")
        self._music.set_volume(float(value))

    def destroy(self) -> None:
        """Free the track.  Idempotent."""
        if self._destroyed:
            return
        self._music.destroy()
        self._destroyed = True


__all__ = ["Music"]
