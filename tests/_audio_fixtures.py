"""Helpers that synthesize tiny valid WAV files for audio tests.

The null/stub backends only need the file to exist, but the SDL2 backend
must be able to actually decode it, so these produce real, well-formed PCM
WAV data (which the bundled SDL_mixer loads without any extra library).
"""

from __future__ import annotations

import struct

RIFF_MAGIC = b"RIFF"
WAVE_MAGIC = b"WAVE"


def wav_bytes(seconds: float = 0.1, sample_rate: int = 8000, frequency: int = 440) -> bytes:
    """Return a tiny mono 16-bit PCM WAV as bytes."""
    sample_count = int(sample_rate * seconds)
    if sample_count < 1:
        sample_count = 1
    frames = bytearray()
    for i in range(sample_count):
        value = int(16000 * (0.5 + 0.5 * __import__("math").sin(2 * __import__("math").pi * frequency * i / sample_rate)))
        frames += struct.pack("<h", value)
    data_size = len(frames)
    fmt = struct.pack(
        "<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16
    )
    riff_size = 4 + (8 + len(fmt)) + (8 + data_size)
    header = (
        RIFF_MAGIC
        + struct.pack("<I", riff_size)
        + WAVE_MAGIC
        + b"fmt "
        + struct.pack("<I", len(fmt))
        + fmt
        + b"data"
        + struct.pack("<I", data_size)
    )
    return header + bytes(frames)


def write_wav(directory: str, name: str, **kwargs) -> str:
    import os

    path = os.path.join(directory, name)
    with open(path, "wb") as handle:
        handle.write(wav_bytes(**kwargs))
    return path
