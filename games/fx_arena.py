"""PYDEX field-test: FX Arena (audio + animation + camera effects).

Exercises the ``Audio`` facade (``load_sound``, ``play_music``) plus the
direct ``Sound`` class, ``SpriteSheet``-built ``Animation`` with
``play_animation``, the ``Keys`` enum for input, a ``Camera2D`` with
``dead_zone``, ``zoom``, ``shake`` and ``screen_to_world``/``world_to_screen``,
mouse input (``is_button_pressed`` + ``mouse_position``), and sprite FX
like ``fade_to`` and ``flash``.  Drive the ball around the arena, collect
the coins, and click to leave expanding shockwave rings.

Controls
--------
* **Arrows** — move the ball (Keys enum input)
* **Space** — bounce FX + camera shake
* **Q / E** — zoom the camera out / in
* **Click** — leave a shockwave ring at the world point you clicked
* **ESC** — quit

Run with:  python games/fx_arena.py
"""

from __future__ import annotations

import os
import random
import tempfile

from _gen import blank, melody, sheet_png, solid_pixels, stamp, tone, wav_bytes

import pydex_ge

W, H = 800, 600
WORLD_W, WORLD_H = 1600, 1200
CELL = 16
SPEED = 300.0


# -- pixel art -------------------------------------------------------------


def ball_frame(squash: tuple[float, float]) -> list[list[tuple[int, int, int, int]]]:
    body = (255, 120, 80, 255)
    outline = (60, 40, 70, 255)
    eye = (30, 30, 30, 255)
    cell = blank(CELL)
    for row in range(CELL):
        for col in range(CELL):
            dx = (col - 7.5) * squash[0]
            dy = (row - 7.5) * squash[1]
            d2 = dx * dx + dy * dy
            if d2 <= 40.0:
                cell[row][col] = body
            elif d2 <= 46.0:
                cell[row][col] = outline
    stamp(cell, 6, 7, 1, 1, eye)
    stamp(cell, 9, 7, 1, 1, eye)
    return cell


def crosshair_pixels() -> bytes:
    size = 14
    pixels = bytearray(size * size * 4)
    for row in range(size):
        for col in range(size):
            if row in (0, size - 1) or col in (0, size - 1):
                color = (130, 205, 255, 255)
            elif abs(row - 6.5) < 1 or abs(col - 6.5) < 1:
                color = (130, 205, 255, 110)
            else:
                color = (0, 0, 0, 0)
            index = (row * size + col) * 4
            pixels[index:index + 4] = bytes(color)
    return bytes(pixels)


# -- application -----------------------------------------------------------


class FxArenaGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX FX Arena", W, H, fps=60)
        self.background = (18, 16, 26)

        # -- runtime assets (generated, nothing committed) ---------------
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name

        self.ball_sheet_path = os.path.join(base, "ball.png")
        with open(self.ball_sheet_path, "wb") as handle:
            handle.write(sheet_png([
                ball_frame((1.00, 1.15)),
                ball_frame((1.30, 0.85)),
                ball_frame((1.00, 1.15)),
                ball_frame((0.85, 1.30)),
            ], size=CELL))

        def write_wav(name: str, samples) -> str:
            path = os.path.join(base, name)
            with open(path, "wb") as handle:
                handle.write(wav_bytes(samples))
            return path

        self.boop_path = write_wav("boop.wav", tone(660, 0.09))
        self.bounce_path = write_wav("bounce.wav", tone(520, 0.05) + tone(760, 0.07))
        self.pickup_path = write_wav("pickup.wav", tone(880, 0.06) + tone(1174, 0.10))
        self.music_path = write_wav(
            "music.wav",
            melody([(262, 0.20), (330, 0.20), (392, 0.20), (523, 0.22),
                    (392, 0.20), (330, 0.20), (262, 0.20), (294, 0.22),
                    (330, 0.20), (392, 0.20), (440, 0.20), (523, 0.22),
                    (659, 0.20), (523, 0.20), (392, 0.20), (330, 0.22)]),
        )

        # -- audio facade + direct Sound/Music ----------------------------
        self.audio = pydex_ge.Audio(backend=self._backend)
        self.boop = pydex_ge.Sound(self.boop_path, backend=self._backend)
        self.bounce = pydex_ge.Sound(self.bounce_path, backend=self._backend)
        self.pickup = self.audio.load_sound(self.pickup_path)
        self.audio.master_volume = 0.9
        self.audio.sound_volume = 0.8
        self.audio.music_volume = 0.45
        self.audio.play_music(self.music_path)

        # -- assets --------------------------------------------------------
        self.assets = pydex_ge.Assets()
        self.sheet = self.assets.sprite_sheet(self.ball_sheet_path, CELL, CELL)
        self.ball = pydex_ge.Sprite(self.sheet.image)
        self.ball.scale_x = 2.0
        self.ball.scale_y = 2.0
        self.ball.position = (WORLD_W // 2, WORLD_H // 2)
        self.ball.animations["bounce"] = self.sheet.animation(
            [(0, 0), (1, 0), (2, 0), (3, 0), (2, 0), (1, 0)], fps=14, loop=True
        )
        self.ball.play_animation("bounce")
        self.ball.flip_x = False

        # -- coins ----------------------------------------------------------
        self.coins = []
        for _ in range(6):
            coin = pydex_ge.Sprite.from_pixels(
                16, 16, solid_pixels(16, 16, (255, 205, 60))
            )
            coin.position = self._random_coin_pos()
            self.coins.append(coin)

        # -- camera & effects lists ----------------------------------------
        self.camera = pydex_ge.Camera2D(W, H, position=(W // 2, H // 2))
        self.camera.bounds = pydex_ge.Rect(0, 0, WORLD_W, WORLD_H)
        self.camera.follow(self.ball, smoothing=4.0)
        self.camera.dead_zone = (160, 100)

        self.rings: list[dict] = []
        self.cursor = pydex_ge.Sprite.from_pixels(14, 14, crosshair_pixels())

        # -- HUD -------------------------------------------------------------
        self.score_label = pydex_ge.Label(
            "Coins: 6", font=pydex_ge.Font(size=16), position=(12, 12),
            color=(255, 220, 120),
        )
        self.mode_label = pydex_ge.Label(
            "camera zoom 1.00 follow smoothing 4", font=pydex_ge.Font(size=14),
            position=(12, 36), color=(180, 200, 220),
        )
        self.hint_label = pydex_ge.Label(
            "Arrows: move   Space: bounce   Q/E: zoom   Click: ring   ESC: quit",
            font=pydex_ge.Font(size=13), position=(12, 58), color=(120, 140, 165),
        )
        self.click_count = 0

    def _random_coin_pos(self) -> tuple[int, int]:
        return (
            random.randint(80, WORLD_W - 80),
            random.randint(80, WORLD_H - 80),
        )

    def _ring_color(self) -> tuple[int, int, int]:
        palette = [(120, 220, 255), (255, 170, 120), (170, 255, 140), (255, 230, 120)]
        return palette[self.click_count % len(palette)]

    # -- loop hooks ---------------------------------------------------------

    def update(self, dt: float) -> None:
        # Movement through the Keys enum (pydex_ge.Keys.LEFT etc.).
        dx = dy = 0.0
        if self.input.is_key_down(pydex_ge.Keys.LEFT):
            dx -= SPEED
        if self.input.is_key_down(pydex_ge.Keys.RIGHT):
            dx += SPEED
        if self.input.is_key_down(pydex_ge.Keys.UP):
            dy -= SPEED
        if self.input.is_key_down(pydex_ge.Keys.DOWN):
            dy += SPEED
        self.ball.x += int(dx * dt)
        self.ball.y += int(dy * dt)
        self.ball.x = max(0, min(self.ball.x, WORLD_W - 32))
        self.ball.y = max(0, min(self.ball.y, WORLD_H - 32))
        self.ball.flip_x = dx < 0

        # Space: bounce FX + shake + sound.
        if self.input.is_key_pressed("space"):
            self.boop.play()
            self.camera.shake(5, 0.2)
            self.ball.play_animation("bounce")

        # Q / E zoom.
        if self.input.is_key_pressed("q"):
            self.camera.zoom = max(0.5, self.camera.zoom - 0.15)
        if self.input.is_key_pressed("e"):
            self.camera.zoom = min(2.0, self.camera.zoom + 0.15)

        # Mouse click -> shockwave ring at the world point (screen_to_world).
        if self.input.is_button_pressed("left"):
            mx, my = self.input.mouse_position
            world = self.camera.screen_to_world((mx, my))
            self.rings.append({
                "x": world.x, "y": world.y, "r": 8.0,
                "max": 120.0 / max(0.5, self.camera.zoom),
            })
            self.bounce.play()
            self.camera.shake(4, 0.15)
            self.click_count += 1

        self.camera.update(dt)
        self.ball.flash(0.3)

        # Collect coins (collect respawns the coin with a fade-in).
        for coin in list(self.coins):
            if (coin.x - self.ball.x) ** 2 + (coin.y - self.ball.y) ** 2 <= 48 ** 2:
                self.pickup.play()
                coin.alpha = 0
                coin.position = self._random_coin_pos()
                coin.fade_to(255, 0.5)
                print("[fx] coin collected")
                self.camera.shake(3, 0.1)

        # Advance shockwave rings (shrinking alpha as they expand).
        alive = []
        for ring in self.rings:
            ring["r"] += 260 * dt
            if ring["r"] < ring["max"]:
                alive.append(ring)
        self.rings = alive

        self.score_label.text = f"Coins: {len(self.coins)}"
        self.mode_label.text = (
            f"camera zoom {self.camera.zoom:.2f} clicks {self.click_count}"
        )

        if self.input.is_key_pressed(pydex_ge.Keys.ESCAPE):
            self.close()

    def draw(self) -> None:
        self.camera.begin(self.renderer)

        # World-space grid, projected with world_to_screen.
        step = 80
        for gx in range(0, WORLD_W + 1, step):
            sx, sx_y = self.camera.world_to_screen((gx, 0))
            self.renderer.draw.line(int(sx), 0, int(sx), H, color=(40, 44, 66))
        for gy in range(0, WORLD_H + 1, step):
            sy_x, sy = self.camera.world_to_screen((0, gy))
            self.renderer.draw.line(0, int(sy), W, int(sy), color=(40, 44, 66))

        for coin in self.coins:
            coin.draw(self.renderer)

        for ring in self.rings:
            sx, sy = self.camera.world_to_screen((ring["x"], ring["y"]))
            self.renderer.draw.circle(
                int(sx), int(sy), int(ring["r"]),
                color=(*self._ring_color(), 255), filled=False,
            )

        self.ball.draw(self.renderer)
        self.camera.end()

        # Screen-space cursor + HUD.
        mx, my = self.input.mouse_position
        self.cursor.position = (mx - 7, my - 7)
        self.renderer.draw_sprite(self.cursor)
        self.renderer.draw_label(self.score_label)
        self.renderer.draw_label(self.mode_label)
        self.renderer.draw_label(self.hint_label)

    def close(self) -> None:
        self.assets.clear()
        self.audio.close()
        self._tmp.cleanup()
        super().close()


def make_game() -> pydex_ge.Game:
    return FxArenaGame()


def main() -> None:
    print("PYDEX FX Arena - drag the ball around, grab coins, click for rings.")
    make_game().run()
    print("FxArenaGame closed cleanly.")


if __name__ == "__main__":
    main()