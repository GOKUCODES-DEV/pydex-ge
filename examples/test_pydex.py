"""PYDEX manual feature test.

Opens a real SDL2 window and exercises the current PYDEX features all at
once, showing each result on screen:

* rendering primitives (rect, circle, line),
* sprites (``Sprite.from_pixels``) moved with a ``Vector2``,
* labels and fonts,
* keyboard input (arrow keys, E, ESC),
* mouse input (click the red target rectangle),
* audio (press E to play a generated beep),
* ``Vector2``/``Rect`` and the collision predicates.

Controls
--------
* **Arrow keys** — steer the blue sprite (clamped to the window with
  ``Rect``).
* **E** — play the beep sound and mark the audio test green.
* **Click** the red rectangle — mark mouse + collision green.
* **ESC** — quit.

Run with:  python examples/test_pydex.py
"""

from __future__ import annotations

import math
import os
import struct
import tempfile
import wave

import pydex_ge
from pydex_ge.physics import (
    Rect,
    Vector2,
    circle_rect_overlap,
    circles_overlap,
    point_in_circle,
    point_in_rect,
    rects_overlap,
)


def _write_tone(path: str, frequency: int = 700, seconds: float = 0.25) -> None:
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


class TestPydex(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Feature Test", 640, 480, fps=60)
        self.background = (18, 18, 24)

        # Audio: generate a tone so no asset files are needed.
        self._tmpdir = tempfile.TemporaryDirectory()
        self.beep_path = os.path.join(self._tmpdir.name, "beep.wav")
        _write_tone(self.beep_path)
        self.audio = pydex_ge.Audio(backend=self._backend)
        self.beep = self.audio.load_sound(self.beep_path)

        # Physics objects.
        self.position = Vector2(120, 240)
        self.velocity = Vector2(0, 0)
        self.speed = 240.0
        self.target_rect = Rect(460, 120, 120, 120)
        self.window_rect = Rect(0, 0, 640, 480)

        # Sprites.
        self.player = pydex_ge.Sprite.from_pixels(24, 24, self._blue_pixels())
        self.player.position = (int(self.position.x), int(self.position.y))

        # Labels / fonts.
        title_font = pydex_ge.Font(size=24)
        status_font = pydex_ge.Font(size=16)
        small_font = pydex_ge.Font(size=13)
        self.title = pydex_ge.Label("PYDEX feature test", font=title_font, position=(20, 16))
        self.hint = pydex_ge.Label(
            "Arrow keys: move   E: beep   Click red box: mouse/collision   ESC: quit",
            font=small_font,
            position=(20, 48),
            color=(140, 150, 170),
        )

        self.status = {}
        row = 88
        for label in ("rendering", "sprite", "labels/fonts", "keyboard", "mouse",
                      "audio", "vector2/rect", "collision"):
            self.status[label] = pydex_ge.Label(
                "  " + label + ":  ...",
                font=status_font,
                position=(20, row),
                color=(200, 200, 210),
            )
            row += 26

        self.status["rendering"].text = "  rendering:  OK (see shapes above)"
        self.status["sprite"].text = "  sprite:     OK (blue square, arrow keys)"
        self.status["labels/fonts"].text = "  labels:     OK (this text)"
        self.status["vector2/rect"].text = "  vector2/rect: OK (sprite moves & stays in window)"
        self._key_pressed_flag = False
        self._mouse_clicked = False

        # --- small math test -------------------------------------------
        # Pre-computed results shown with Labels; the sprite movement below
        # uses the same Vector2/Rect/collision math live.
        a = Vector2(3, 4)
        b = Vector2(5, 6)
        self.math_checks = {
            "add": ("Vector2(3,4) + (5,6)", a + b),
            "mul": ("(3,4) * 2", a * 2),
            "length": ("(3,4).length", a.length),
            "normalized": ("(3,4).normalized()", a.normalized()),
            "rotate90": ("(1,0).rotate(90)", Vector2(1, 0).rotate(90)),
            "rect_moved": ("Rect(10,20,30,40).moved(5,5)",
                           Rect(10, 20, 30, 40).moved(5, 5)),
            "rect_overlap": ("Rect(0,0,10,10) overlaps (5,5,10,10)",
                             rects_overlap(Rect(0, 0, 10, 10), Rect(5, 5, 10, 10))),
            "point_in_rect": ("point_in_rect((5,5), Rect(0,0,10,10))",
                              point_in_rect((5, 5), Rect(0, 0, 10, 10))),
            "circles": ("circles_overlap((0,0),5,(3,4),5)",
                        circles_overlap((0, 0), 5, (3, 4), 5)),
            "point_in_circle": ("point_in_circle((1,1),(0,0),2)",
                                point_in_circle((1, 1), (0, 0), 2)),
            "circle_rect": ("circle_rect_overlap((0,0),3,Rect(0,0,10,10))",
                            circle_rect_overlap((0, 0), 3, Rect(0, 0, 10, 10))),
        }
        math_font = pydex_ge.Font(size=13)
        self.math_title = pydex_ge.Label(
            "Math test (Vector2 / Rect / collision)", font=status_font,
            position=(20, 280), color=(255, 220, 120),
        )
        self.math_lines = {}
        for index, (name, (expr, value)) in enumerate(self.math_checks.items()):
            self.math_lines[name] = pydex_ge.Label(
                f"  {expr} = {value}",
                font=math_font,
                position=(20, 300 + index * 14),
                color=(180, 200, 210),
            )
        self.math_live = pydex_ge.Label(
            "  live: pos (0,0) vel (0,0)", font=math_font,
            position=(20, 300 + len(self.math_checks) * 14),
            color=(120, 255, 120),
        )

    @staticmethod
    def _blue_pixels() -> bytes:
        """A 24x24 RGBA pixel sprite: a solid blue square."""
        size = 24
        pixels = bytearray(size * size * 4)
        for index in range(size * size):
            start = index * 4
            pixels[start:start + 4] = bytes((80, 160, 255, 255))
        return bytes(pixels)

    def update(self, dt: float) -> None:
        # Keyboard input: arrow keys build a velocity vector.
        self.velocity = Vector2(0, 0)
        if self.input.is_key_down("left"):
            self.velocity -= Vector2(self.speed, 0)
        if self.input.is_key_down("right"):
            self.velocity += Vector2(self.speed, 0)
        if self.input.is_key_down("up"):
            self.velocity -= Vector2(0, self.speed)
        if self.input.is_key_down("down"):
            self.velocity += Vector2(0, self.speed)
        self.position += self.velocity * dt

        # Clamp to the window using a Rect.
        body = Rect(self.position.x, self.position.y, 24, 24)
        if body.left < self.window_rect.left:
            self.position.x = self.window_rect.left
        if body.right > self.window_rect.right:
            self.position.x = self.window_rect.right - 24
        if body.top < self.window_rect.top:
            self.position.y = self.window_rect.top
        if body.bottom > self.window_rect.bottom:
            self.position.y = self.window_rect.bottom - 24
        self.player.position = (int(self.position.x), int(self.position.y))

        # Live math readout: the sprite movement above uses Vector2 math,
        # so show the current position and velocity.
        self.math_live.text = (
            f"  live: pos ({int(self.position.x)},{int(self.position.y)}) "
            f"vel ({int(self.velocity.x)},{int(self.velocity.y)})"
        )

        # Audio + keyboard test: E plays the beep.
        if self.input.is_key_pressed("e"):
            self.beep.play()
            self._key_pressed_flag = True
            self.status["audio"].text = "  audio:      OK (beeped)"
            self.status["audio"].color = (120, 255, 120)
            self.status["keyboard"].text = "  keyboard:   OK (E detected)"
            self.status["keyboard"].color = (120, 255, 120)

        # Mouse input: clicking the red box fires the collision predicate.
        if self.input.is_button_pressed("left"):
            mx, my = self.input.mouse_position
            if self.target_rect.contains_point((mx, my)):
                self._mouse_clicked = True
                self.status["mouse"].text = f"  mouse:      OK (clicked at {mx},{my})"
                self.status["mouse"].color = (120, 255, 120)
                self.status["collision"].text = "  collision:  OK (point_in_rect)"
                self.status["collision"].color = (120, 255, 120)

        # Sprite/rect overlap collision feedback.
        if body.overlaps(self.target_rect):
            self.status["collision"].text = "  collision:  OK (sprite overlaps box)"
            self.status["collision"].color = (255, 220, 80)

        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        # Rendering primitives.
        self.renderer.draw.rect(460, 120, 120, 120, color=(255, 90, 90, 255))
        self.renderer.draw.rect(460, 120, 120, 120, color=(255, 255, 255, 255), filled=False)
        self.renderer.draw.circle(560, 420, 30, color=(255, 200, 60, 255))
        self.renderer.draw.circle(560, 420, 30, color=(255, 255, 255, 255), filled=False)
        self.renderer.draw.line(40, 420, 160, 420, color=(120, 220, 120, 255))

        # Sprites.
        self.renderer.draw_sprite(self.player)

        # Labels.
        self.renderer.draw_label(self.title)
        self.renderer.draw_label(self.hint)
        for label in self.status.values():
            self.renderer.draw_label(label)

        # Math test labels.
        self.renderer.draw_label(self.math_title)
        for label in self.math_lines.values():
            self.renderer.draw_label(label)
        self.renderer.draw_label(self.math_live)

    def close(self) -> None:
        self.audio.close()
        self._tmpdir.cleanup()
        super().close()


def main() -> None:
    print("PYDEX feature test - arrow keys move, E beeps, click the red box, ESC quits.")
    game = TestPydex()
    game.run()
    print("Feature test closed cleanly.")


if __name__ == "__main__":
    main()
