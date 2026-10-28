"""PYDEX combined example: input + sound + labels.

Demonstrates the three subsystems working together in one window:

* A **label** shows instructions and live status.
* Press **E** -> a **sound** effect plays and the label updates.
* Press **E** again -> the window closes.
* **ESC** also closes.

The sound is generated at startup (a short test tone), so no asset files
are needed.

Run with:  python examples/input_sound_label.py
"""

from __future__ import annotations

import math
import os
import struct
import tempfile
import wave

import pydex_ge


def _write_tone(path: str, frequency: int = 660, seconds: float = 0.3) -> None:
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


class InputSoundLabelGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Input + Sound + Label", 640, 480, fps=60)
        self.background = (18, 18, 24)

        self._tmpdir = tempfile.TemporaryDirectory()
        self.sound_path = os.path.join(self._tmpdir.name, "beep.wav")
        _write_tone(self.sound_path)

        self.audio = pydex_ge.Audio(backend=self._backend)
        self.beep = self.audio.load_sound(self.sound_path)

        font = pydex_ge.Font(size=32)
        self.prompt = pydex_ge.Label("Press E to hear a sound", font=font, position=(120, 200))
        self.hint = pydex_ge.Label(
            "E: sound + label     E again (or ESC): quit",
            font=pydex_ge.Font(size=16),
            position=(120, 260),
            color=(120, 130, 150),
        )
        self._presses = 0

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("e"):
            self._presses += 1
            if self._presses == 1:
                self.beep.play()
                self.prompt.text = "Sound playing!"
                self.prompt.color = (120, 255, 120)
            else:
                self.prompt.text = "Goodbye!"
                self.close()
        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        self.renderer.draw_label(self.prompt)
        self.renderer.draw_label(self.hint)

    def close(self) -> None:
        self.audio.close()
        self._tmpdir.cleanup()
        super().close()


def main() -> None:
    game = InputSoundLabelGame()
    print("Press E to play a sound; press E again (or ESC) to quit.")
    game.run()
    print("InputSoundLabelGame closed cleanly.")


if __name__ == "__main__":
    main()
