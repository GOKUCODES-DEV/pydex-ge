"""PYDEX Part 6 example: audio.

Opens a real SDL2 window with sound and music.  A small test tone is
generated at startup (no asset files needed) and is looped so the audio
is easy to hear and control.

Keys:
    1          play the sound effect
    2          play music (looping)
    3          pause music
    4          resume music
    5          stop music
    + / -      raise / lower the master volume
    ESC        quit

Run with:  python examples/audio.py
"""

from __future__ import annotations

import math
import os
import struct
import tempfile
import wave

import pydex_ge


def _write_tone(path: str, frequency: int, seconds: float = 0.5) -> None:
    """Write a short pure-tone WAV file (44100 Hz, 16-bit mono)."""
    rate = 44100
    n = int(rate * seconds)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            value = int(0.4 * 32767 * math.sin(2 * math.pi * frequency * i / rate))
            frames += struct.pack("<h", value)
        w.writeframes(bytes(frames))


class AudioDemo(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Audio", 640, 480, fps=60)
        self.background = (18, 18, 24)

        self._tmpdir = tempfile.TemporaryDirectory()
        self.sound_path = os.path.join(self._tmpdir.name, "beep.wav")
        self.music_path = os.path.join(self._tmpdir.name, "tone.wav")
        _write_tone(self.sound_path, 880, 0.25)
        _write_tone(self.music_path, 220, 2.0)

        self.audio = pydex_ge.Audio(backend=self._backend)
        self.sound = self.audio.load_sound(self.sound_path)
        self.music = self.audio.load_music(self.music_path)

        font = pydex_ge.Font(size=20)
        self.title = pydex_ge.Label("Audio: 1=sound  2=music  3=pause  4=resume  5=stop", font=font, position=(40, 60))
        self.hint = pydex_ge.Label("+ / - volume    ESC: quit", font=pydex_ge.Font(size=16), position=(40, 90), color=(120, 130, 150))
        self.status = pydex_ge.Label("", font=font, position=(40, 140), color=(120, 255, 120))

        self._last_keys = ""

    def update(self, dt: float) -> None:
        status = []
        if self.input.is_key_pressed("1"):
            self.sound.play(loop=True)
            status.append("sound playing")
        if self.input.is_key_pressed("2"):
            self.music.play(loop=True)
            status.append("music playing")
        if self.input.is_key_pressed("3"):
            self.music.pause()
            status.append("music paused")
        if self.input.is_key_pressed("4"):
            self.music.resume()
            status.append("music resumed")
        if self.input.is_key_pressed("5"):
            self.music.stop()
            status.append("music stopped")
        if self.input.is_key_pressed("+"):
            self.audio.master_volume = min(1.0, self.audio.master_volume + 0.1)
            status.append(f"master volume = {self.audio.master_volume:.1f}")
        if self.input.is_key_pressed("-"):
            self.audio.master_volume = max(0.0, self.audio.master_volume - 0.1)
            status.append(f"master volume = {self.audio.master_volume:.1f}")

        if status:
            self._last_keys = "  |  ".join(status)
        self.status.text = (
            f"{self._last_keys}\n"
            f"sound playing={self.sound.playing}  music playing={self.music.playing}  "
            f"music paused={self.music.paused}"
        )
        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        self.renderer.draw_label(self.title)
        self.renderer.draw_label(self.hint)
        self.renderer.draw_label(self.status)

    def close(self) -> None:
        self.audio.close()
        self._tmpdir.cleanup()
        super().close()


def main() -> None:
    print("PYDEX audio example - keys: 1 sound, 2 music, 3 pause, 4 resume, 5 stop, +/- volume, ESC quit.")
    game = AudioDemo()
    game.run()
    print("AudioDemo closed cleanly.")


if __name__ == "__main__":
    main()
