"""PYDEX Part 7.5 example: Body, World, gravity, and a floor collision.

Opens a real SDL2 window with a simple physics world:

* a :class:`~pydex_ge.physics.Body` (a ``Sprite.from_pixels`` box) falls
  under gravity,
* a floor :class:`~pydex_ge.physics.Rect` catches it via static-rectangle
  collision resolution, and
* a :class:`Label` shows the live position, velocity, and grounded state.

Controls
--------
* **R** — drop the box again from the top.
* **Space** — give the box a little upward impulse (a hop).
* **ESC** — quit.

Run with:  python examples/falling.py
"""

from __future__ import annotations

import pydex_ge
from pydex_ge.physics import Body, Rect, World


class FallingGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Falling (Body + World)", 640, 480, fps=60)
        self.background = (18, 18, 24)

        self.floor = Rect(0, 440, 640, 40)
        self.wall_left = Rect(0, 0, 8, 480)
        self.wall_right = Rect(632, 0, 8, 480)
        self.world = World(
            gravity=(0, 700),
            static_rects=(self.floor, self.wall_left, self.wall_right),
        )
        self.body = Body(
            position=(300, 40),
            size=(40, 40),
            velocity=(80, 0),
        )
        self.world.add_body(self.body)

        self.sprite = pydex_ge.Sprite.from_pixels(40, 40, self._pixels())
        self.sprite.position = (int(self.body.position.x), int(self.body.position.y))

        font = pydex_ge.Font(size=16)
        small = pydex_ge.Font(size=13)
        self.hint = pydex_ge.Label(
            "R: drop again    Space: hop    ESC: quit",
            font=small,
            position=(20, 20),
            color=(120, 130, 150),
        )
        self.info = pydex_ge.Label(
            "pos (0,0) vel (0,0) grounded: no",
            font=font,
            position=(20, 48),
            color=(120, 255, 120),
        )

    @staticmethod
    def _pixels() -> bytes:
        """A 40x40 RGBA pixel sprite (a plain bright square)."""
        size = 40
        pixels = bytearray(size * size * 4)
        for index in range(size * size):
            start = index * 4
            pixels[start:start + 4] = bytes((120, 220, 255, 255))
        return bytes(pixels)

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("r"):
            self.body.position = (300, 40)
            self.body.velocity = (80, 0)
            self.body.acceleration = (0, 0)
        if self.input.is_key_pressed("space"):
            self.body.apply_impulse((0, -260))

        self.world.update(dt)

        grounded = self.body.collides_with(self.floor) and self.body.velocity.y == 0
        self.info.text = (
            f"pos ({int(self.body.position.x)},{int(self.body.position.y)}) "
            f"vel ({int(self.body.velocity.x)},{int(self.body.velocity.y)}) "
            f"grounded: {'yes' if grounded else 'no'}"
        )
        self.sprite.position = (int(self.body.position.x), int(self.body.position.y))

        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        for rect in (self.wall_left, self.wall_right):
            self.renderer.draw.rect(
                int(rect.x), int(rect.y),
                int(rect.width), int(rect.height),
                color=(90, 110, 150, 255),
            )
        self.renderer.draw.rect(
            int(self.floor.x), int(self.floor.y),
            int(self.floor.width), int(self.floor.height),
            color=(90, 110, 150, 255),
        )
        self.renderer.draw_sprite(self.sprite)
        self.renderer.draw_label(self.hint)
        self.renderer.draw_label(self.info)


def main() -> None:
    game = FallingGame()
    print("PYDEX falling example - a body drops under gravity and lands on a floor.")
    print("Press R to drop again, Space to hop, ESC to quit.")
    game.run()
    print("FallingGame closed cleanly.")


if __name__ == "__main__":
    main()
