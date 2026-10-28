"""PYDEX Part 7 example: Vector2, Rect, and collision predicates.

Opens a real SDL2 window with a moving sprite (built with
``Sprite.from_pixels``) that:

* is steered with the **arrow keys** through a :class:`~pydex_ge.physics.Vector2`
  velocity, and
* bounces off the window edges using :class:`~pydex_ge.physics.Rect` overlap
  checks (pure geometry — no physics engine).

A stationary target rectangle is drawn; when the sprite overlaps it, the
target flashes to show the collision predicate firing.  **ESC** quits.

Run with:  python examples/physics.py
"""

from __future__ import annotations

import pydex_ge
from pydex_ge.physics import Rect, Vector2


class PhysicsDemo(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Physics (geometry)", 640, 480, fps=60)
        self.background = (18, 18, 24)

        self.position = Vector2(300, 200)
        self.velocity = Vector2(180, 140)
        self.sprite = pydex_ge.Sprite.from_pixels(24, 24, self._pixels())
        self.sprite.position = (int(self.position.x), int(self.position.y))

        self.target = Rect(500, 40, 90, 90)
        self._hit = 0.0

        font = pydex_ge.Font(size=16)
        self.hint = pydex_ge.Label(
            "Arrow keys steer    ESC: quit",
            font=font,
            position=(20, 20),
            color=(120, 130, 150),
        )

    @staticmethod
    def _pixels() -> bytes:
        """A 24x24 RGBA pixel sprite (a plain bright square)."""
        size = 24
        pixels = bytearray(size * size * 4)
        for index in range(size * size):
            start = index * 4
            pixels[start:start + 4] = bytes((120, 220, 255, 255))
        return bytes(pixels)

    def update(self, dt: float) -> None:
        speed = 220.0
        move = Vector2(0, 0)
        if self.input.is_key_down("left"):
            move -= Vector2(speed, 0)
        if self.input.is_key_down("right"):
            move += Vector2(speed, 0)
        if self.input.is_key_down("up"):
            move -= Vector2(0, speed)
        if self.input.is_key_down("down"):
            move += Vector2(0, speed)
        self.velocity = move if move.length > 0 else self.velocity

        self.position += self.velocity * dt

        bounds = Rect(0, 0, self.window.width, self.window.height)
        body = Rect(self.position.x, self.position.y, 24, 24)
        if body.left < bounds.left:
            self.position.x = bounds.left
            self.velocity.x = abs(self.velocity.x)
        if body.right > bounds.right:
            self.position.x = bounds.right - 24
            self.velocity.x = -abs(self.velocity.x)
        if body.top < bounds.top:
            self.position.y = bounds.top
            self.velocity.y = abs(self.velocity.y)
        if body.bottom > bounds.bottom:
            self.position.y = bounds.bottom - 24
            self.velocity.y = -abs(self.velocity.y)

        self.sprite.position = (int(self.position.x), int(self.position.y))

        self._hit = max(0.0, self._hit - dt)
        if body.overlaps(self.target):
            self._hit = 0.35

        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        self.renderer.draw.rect(
            int(self.target.x), int(self.target.y),
            int(self.target.width), int(self.target.height),
            color=(255, 120, 120, 255),
        )
        if self._hit > 0:
            self.renderer.draw.rect(
                int(self.target.x) - 4, int(self.target.y) - 4,
                int(self.target.width) + 8, int(self.target.height) + 8,
                color=(255, 255, 255, 255),
            )
        self.renderer.draw_sprite(self.sprite)
        self.renderer.draw_label(self.hint)


def main() -> None:
    game = PhysicsDemo()
    print("PYDEX physics example - arrow keys steer, sprite bounces off edges.")
    print("Steer into the red rectangle to trigger the collision highlight.")
    game.run()
    print("PhysicsDemo closed cleanly.")


if __name__ == "__main__":
    main()
