"""PYDEX audio: sound effects, music, and an audio manager.

This package exposes three friendly, beginner-oriented objects:

* :class:`~pydex_ge.audio.sound.Sound` - a reusable sound effect (WAV and other
  chunk formats) that can overlap with other sounds.
* :class:`~pydex_ge.audio.music.Music` - a music track; only one plays at a time.
* :class:`~pydex_ge.audio.manager.Audio` - a convenient manager that bundles
  master/sound/music volume, loading helpers, global controls, and cleanup.

All audio is loaded directly from the developer's project folders (e.g. an
``assets/audio/`` directory); nothing is installed into the operating system.
Relative paths resolve against the process working directory, absolute paths
are used as-is.

Volume is expressed on a simple ``0.0`` (silent) to ``1.0`` (full) scale and
is validated on every setter.
"""

from .manager import Audio
from .music import Music
from .sound import Sound

__all__ = ["Audio", "Music", "Sound"]
