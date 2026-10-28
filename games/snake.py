"""PYDEX field-test: Snake (2D grid game).

Exercises ``Sprite.from_pixels`` (procedural pixel art, no asset files),
``Input``/``Keys``-style input helpers, ``Label`` HUD, tick-based timing,
and self-collision logic.  The snake wraps around the edges of the grid.

Controls
--------
* Arrow keys — steer (180-degree reversals are ignored)
* **R** — restart after a game over
* **ESC** — quit

Run with:  python games/snake.py
"""

from __future__ import annotations

import random

import pydex_ge

CELL = 20
COLS, ROWS = 32, 24
STEP = 0.13
W, H = CELL * COLS, CELL * ROWS
START = [(17, 17), (16, 17), (15, 17)]


def solid_pixels(width: int, height: int, color) -> bytes:
    """A width*height solid RGBA pixel block (no asset files needed)."""
    row = bytes((*color, 255)) * width
    return row * height


class SnakeGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Snake", W, H, fps=60)
        self.background = (12, 16, 22)
        self.font = pydex_ge.Font(size=18)
        self.small_font = pydex_ge.Font(size=13)

        self.score_label = pydex_ge.Label(
            "Score: 0", font=self.font, position=(10, 8), color=(255, 210, 90)
        )
        self.hint_label = pydex_ge.Label(
            "Arrows steer   R restart   ESC quit",
            font=self.small_font,
            position=(10, 32),
            color=(120, 130, 150),
        )
        self.over_label = pydex_ge.Label(
            "Game Over - press R to restart",
            font=pydex_ge.Font(size=22),
            position=(W // 2 - 140, H // 2),
            color=(255, 120, 120),
        )

        self.food = pydex_ge.Sprite.from_pixels(
            CELL, CELL, solid_pixels(CELL, CELL, (235, 80, 80))
        )
        self.segments: list[pydex_ge.Sprite] = []
        self.reset()

    # -- setup ------------------------------------------------------------

    def reset(self) -> None:
        self.snake: list[tuple[int, int]] = list(START)
        self.direction = (1, 0)
        self.pending: list[tuple[int, int]] = []
        self.timer = 0.0
        self.over = False
        self.food_pos = self._random_food()
        self.segments = []

    def _random_food(self) -> tuple[int, int]:
        while True:
            cell = (random.randrange(COLS), random.randrange(ROWS))
            if cell not in self.snake:
                return cell

    # -- loop hooks -------------------------------------------------------

    def update(self, dt: float) -> None:
        self._queue_direction()

        if self.input.is_key_pressed("r"):
            self.reset()
            return

        if self.over:
            if self.input.is_key_pressed("escape"):
                self.close()
            return

        self.timer += dt
        while self.timer >= STEP:
            self.timer -= STEP
            self._step()

        if self.input.is_key_pressed("escape"):
            self.close()
        self.score_label.text = f"Score: {len(self.snake) - len(START)}"

    def draw(self) -> None:
        while len(self.segments) < len(self.snake):
            index = len(self.segments)
            if index == 0:
                color = (150, 240, 120)
            else:
                color = (80, 190, 90)
            self.segments.append(
                pydex_ge.Sprite.from_pixels(CELL, CELL, solid_pixels(CELL, CELL, color))
            )
        for sprite, (cell_x, cell_y) in zip(self.segments, self.snake):
            sprite.position = (cell_x * CELL, cell_y * CELL)
        for sprite in self.segments:
            self.renderer.draw_sprite(sprite)

        self.food.position = (self.food_pos[0] * CELL, self.food_pos[1] * CELL)
        self.renderer.draw_sprite(self.food)

        self.renderer.draw_label(self.score_label)
        self.renderer.draw_label(self.hint_label)
        if self.over:
            self.renderer.draw_label(self.over_label)

    # -- game logic -------------------------------------------------------

    def _queue_direction(self) -> None:
        mapping = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }
        for key, delta in mapping.items():
            if self.input.is_key_pressed(key):
                last = self.pending[-1] if self.pending else self.direction
                if delta != last and delta != (-last[0], -last[1]):
                    self.pending.append(delta)

    def _step(self) -> None:
        while self.pending:
            next_dir = self.pending.pop(0)
            if next_dir != (-self.direction[0], -self.direction[1]):
                self.direction = next_dir
                break

        head = self.snake[0]
        new_head = (
            (head[0] + self.direction[0]) % COLS,
            (head[1] + self.direction[1]) % ROWS,
        )
        self.snake.insert(0, new_head)
        if new_head == self.food_pos:
            self.food_pos = self._random_food()
        else:
            self.snake.pop()
        if new_head in self.snake[1:]:
            self.over = True


def make_game() -> pydex_ge.Game:
    return SnakeGame()


def main() -> None:
    print("PYDEX Snake - arrows steer, eat food, avoid yourself.")
    make_game().run()
    print("SnakeGame closed cleanly.")


if __name__ == "__main__":
    main()