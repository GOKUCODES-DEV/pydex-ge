"""PYDEX field-test: Pong (2D arcade game).

Exercises the renderer's shape primitives (``renderer.draw.rect`` and
``renderer.draw.circle``), manual ball/paddle collision math, an AI
paddle, and ``Label`` scoring.  First to 7 points wins.

Controls
--------
* **W / S** — move the left paddle
* **R** — restart the match
* **ESC** — quit

Run with:  python games/pong.py
"""

from __future__ import annotations

import math
import random

import pydex_ge
from pydex_ge.physics import Rect

W, H = 800, 450
BALL_R = 8
PADDLE_W, PADDLE_H = 12, 90
PADDLE_OFFSET = 30
PLAYER_SPEED = 330.0
AI_SPEED = 240.0
BALL_SPEED = 320.0
WIN_SCORE = 7


class PongGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Pong", W, H, fps=60)
        self.background = (8, 12, 18)

        self.paddle_left = Rect(PADDLE_OFFSET, H // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
        self.paddle_right = Rect(W - PADDLE_OFFSET - PADDLE_W, H // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)

        self.score_label = pydex_ge.Label(
            "0 : 0", font=pydex_ge.Font(size=36), position=(W // 2 - 42, 18), color=(255, 255, 255)
        )
        self.hint_label = pydex_ge.Label(
            "W/S move   R restart   ESC quit",
            font=pydex_ge.Font(size=13),
            position=(12, 12),
            color=(120, 130, 150),
        )
        self.winner_label = pydex_ge.Label(
            "", font=pydex_ge.Font(size=22), position=(W // 2 - 110, H // 2 + 60), color=(255, 210, 90)
        )

        self.score_left = 0
        self.score_right = 0
        self.winner = ""
        self.ball_x = W / 2
        self.ball_y = H / 2
        self.ball_vx = BALL_SPEED
        self.ball_vy = BALL_SPEED * 0.4

    def _restart(self) -> None:
        self.score_left = 0
        self.score_right = 0
        self.winner = ""
        self.winner_label.text = ""
        self._reset_ball(toward_left=True)

    def _reset_ball(self, *, toward_left: bool) -> None:
        self.ball_x = W / 2
        self.ball_y = H / 2
        angle = math.radians(random.uniform(-35, 35))
        vx = -BALL_SPEED if toward_left else BALL_SPEED
        vy = BALL_SPEED * math.sin(angle) * (1 if random.random() < 0.5 else -1)
        magnitude = math.hypot(vx, vy)
        self.ball_vx = vx / magnitude * BALL_SPEED
        self.ball_vy = vy / magnitude * BALL_SPEED

    def _check_win(self) -> None:
        if self.score_left >= WIN_SCORE:
            self.winner = "You win!"
        elif self.score_right >= WIN_SCORE:
            self.winner = "AI wins - try again!"
        self.winner_label.text = self.winner

    def _bounce(self, paddle: Rect) -> float:
        offset = (self.ball_y - (paddle.y + PADDLE_H / 2)) / (PADDLE_H / 2)
        offset = max(-1.0, min(1.0, offset))
        return offset * BALL_SPEED * 0.75

    # -- loop hooks -------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("escape"):
            self.close()
        if self.input.is_key_pressed("r") or self.winner and self.input.is_key_pressed("return"):
            self._restart()
        if self.winner:
            return

        # Human paddle.
        if self.input.is_key_down("w"):
            self.paddle_left.y -= PLAYER_SPEED * dt
        if self.input.is_key_down("s"):
            self.paddle_left.y += PLAYER_SPEED * dt
        self.paddle_left.y = max(0.0, min(H - PADDLE_H, self.paddle_left.y))

        # AI paddle chases the ball.
        target_y = self.ball_y - PADDLE_H / 2
        if abs(target_y - self.paddle_right.y) > 2:
            step = min(AI_SPEED * dt, abs(target_y - self.paddle_right.y))
            self.paddle_right.y += step if target_y > self.paddle_right.y else -step
        self.paddle_right.y = max(0.0, min(H - PADDLE_H, self.paddle_right.y))

        # Ball movement.
        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt
        if self.ball_y < BALL_R:
            self.ball_y = BALL_R
            self.ball_vy = abs(self.ball_vy)
        elif self.ball_y > H - BALL_R:
            self.ball_y = H - BALL_R
            self.ball_vy = -abs(self.ball_vy)

        # Paddle collisions (bounce off the side facing the ball).
        ball_rect = Rect(self.ball_x - BALL_R, self.ball_y - BALL_R, BALL_R * 2, BALL_R * 2)
        if self.ball_vx < 0 and ball_rect.overlaps(self.paddle_left):
            self.ball_x = self.paddle_left.right + BALL_R
            self.ball_vx = abs(self.ball_vx) * 1.06
            self.ball_vy = self._bounce(self.paddle_left)
        elif self.ball_vx > 0 and ball_rect.overlaps(self.paddle_right):
            self.ball_x = self.paddle_right.x - BALL_R
            self.ball_vx = -abs(self.ball_vx) * 1.06
            self.ball_vy = self._bounce(self.paddle_right)

        # Scoring.
        if self.ball_x < -BALL_R * 2:
            self.score_right += 1
            self._check_win()
            self._reset_ball(toward_left=True)
        elif self.ball_x > W + BALL_R * 2:
            self.score_left += 1
            self._check_win()
            self._reset_ball(toward_left=False)

        self.score_label.text = f"{self.score_left} : {self.score_right}"

    def draw(self) -> None:
        # Center court line.
        for y in range(0, H, 24):
            self.renderer.draw.line(W // 2, y, W // 2, min(y + 12, H), color=(70, 85, 105))

        self.renderer.draw.rect(
            int(self.paddle_left.x), int(self.paddle_left.y), PADDLE_W, PADDLE_H, color=(130, 220, 255)
        )
        self.renderer.draw.rect(
            int(self.paddle_right.x), int(self.paddle_right.y), PADDLE_W, PADDLE_H, color=(255, 150, 130)
        )
        self.renderer.draw.circle(int(self.ball_x), int(self.ball_y), BALL_R, color=(255, 255, 255))

        self.renderer.draw_label(self.hint_label)
        self.renderer.draw_label(self.score_label)
        if self.winner:
            self.renderer.draw_label(self.winner_label)


def make_game() -> pydex_ge.Game:
    return PongGame()


def main() -> None:
    print("PYDEX Pong - W/S move, first to 7 wins.")
    make_game().run()
    print("PongGame closed cleanly.")


if __name__ == "__main__":
    main()