"""PYDEX field-test: Super PYDEX (a Mario-style platformer clone).

A side-scrolling platformer built on the public-domain Kenney "Pixel
Platformer" asset pack (CC0, https://kenney.nl/assets/pixel-platformer).

Controls
--------
* **Left / Right** (or **A / D**) -- run
* **Space** (or **Up / W**) -- jump; release early for a short hop
* **R** -- restart the level
* **ESC** -- quit

Run with:  python games/mario_clone.py
"""

from __future__ import annotations

import math
import os
import random
import struct
import wave

import pydex_ge

W, H = 960, 540
FPS = 60

ASSET_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "kenney_pixel"
)
TILES_PATH = os.path.join(ASSET_DIR, "tilemap_packed.png")
CHARS_PATH = os.path.join(ASSET_DIR, "tilemap-characters_packed.png")

CELL = 72
TILE = 18
CHAR = 24
TILE_SCALE = CELL / TILE
CHAR_SCALE = CELL / CHAR

LEVEL_ROWS = 16
LEVEL_COLS = 44

GRAVITY = 2500.0
JUMP_VELOCITY = -1050.0
RUN_SPEED = 330.0
ACCEL = 2600.0
FRICTION = 3000.0
ENEMY_SPEED = 95.0
TIME_LIMIT = 300
START_LIVES = 3
INVULN_SECONDS = 0.8

SKY = (92, 148, 252)


# ------------------------------------------------------------------
# Procedural "?" / used block pixels (the Kenney char sheet has no "?" tile)
# ------------------------------------------------------------------

_QUESTION_GLYPH = [
    ".###.",
    "#...#",
    "....#",
    "...#.",
    "..#..",
    ".....",
    "..#..",
]


def _box_pixels(question: bool) -> bytes:
    size = CELL
    cell = [[(0, 0, 0, 0)] * size for _ in range(size)]
    outline = (168, 74, 0, 255)
    fill = (240, 168, 0, 255)
    light = (255, 205, 60, 255)
    glyph = (120, 40, 0, 255)
    rivet = (208, 128, 0, 255)
    for yy in range(size):
        row = cell[yy]
        for xx in range(size):
            row[xx] = outline if xx % size in (0, 1, size - 2, size - 1) else fill
    for yy in range(2, size - 2):
        for xx in range(2, size - 2):
            cell[yy][xx] = fill
    for xx in range(2, size - 2):
        cell[1][xx] = light
        cell[size - 2][xx] = outline
    if question:
        scale = 4
        gw, gh = 5 * scale, 7 * scale
        gx0 = (size - gw) // 2
        gy0 = (size - gh) // 2
        for r, text in enumerate(_QUESTION_GLYPH):
            for c, ch in enumerate(text):
                if ch == "#":
                    for yy in range(scale):
                        for xx in range(scale):
                            cell[gy0 + r * scale + yy][gx0 + c * scale + xx] = glyph
    for rx, ry in ((3, 3), (size - 4, 3), (3, size - 4), (size - 4, size - 4)):
        for yy in range(rx, rx + 3):
            for xx in range(ry, ry + 3):
                cell[yy][xx] = rivet
    rows = []
    for row in cell:
        line = bytearray()
        for px in row:
            line += bytes(px)
        rows.append(bytes(line))
    return b"".join(rows)


# ------------------------------------------------------------------
# Level builder
# ------------------------------------------------------------------

def build_level() -> list[list[str]]:
    grid = [[" "] * LEVEL_COLS for _ in range(LEVEL_ROWS)]

    def ground(c0: int, c1: int, surface: int) -> None:
        for col in range(c0, c1 + 1):
            grid[surface][col] = "G"
            for row in range(surface + 1, LEVEL_ROWS):
                grid[row][col] = "X"

    ground(0, 16, 12)
    ground(21, LEVEL_COLS - 1, 12)

    for col in (3, 12, 26, 36):
        grid[1][col] = "c"
    for col in (8, 19, 33):
        grid[3][col] = "c"
    for col in (1, 15, 28, 40):
        grid[5][col] = "b"

    for col in range(8, 12):
        grid[8][col] = "B"
    grid[8][9] = "o"
    grid[8][11] = "?"
    grid[7][14] = "o"

    for col in range(18, 21):
        grid[7][col] = "B"
    grid[6][19] = "o"

    for col in (24, 28, 32):
        grid[5][col] = "?"

    for col in range(36, 40):
        grid[10][col] = "B"
    for col in range(37, 40):
        grid[9][col] = "B"
    for col in range(38, 40):
        grid[8][col] = "B"

    for col in (6, 14, 23, 33):
        grid[11][col] = "E"

    grid[11][2] = "S"

    for row in range(3, 12):
        grid[row][LEVEL_COLS - 2] = "F"

    return grid


# ------------------------------------------------------------------
# Runtime SFX (square waves, stdlib only)
# ------------------------------------------------------------------

_SFX = {
    "jump": ((220, 660, 0.14),),
    "coin": ((988, 1319, 0.10),),
    "brick": ((120, 60, 0.09),),
    "stomp": ((260, 50, 0.13),),
    "oneup": ((660, 990, 0.09), (880, 1320, 0.12)),
}


def _write_wav(path: str, steps: tuple) -> None:
    rate = 22050
    frames = bytearray()
    for start_freq, end_freq, duration in steps:
        count = int(rate * duration)
        for index in range(count):
            t = index / rate
            mix = index / count
            freq = start_freq + (end_freq - start_freq) * mix
            sample = math.sin(2.0 * math.pi * freq * t)
            square = 1.0 if sample >= 0.0 else -1.0
            envelope = 1.0 - 0.6 * mix
            value = int(32767 * square * envelope)
            frames += struct.pack("<h", value)
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))


def ensure_sfx() -> str:
    sfx_dir = os.path.join(ASSET_DIR, "sfx")
    os.makedirs(sfx_dir, exist_ok=True)
    for name, steps in _SFX.items():
        path = os.path.join(sfx_dir, name + ".wav")
        if not os.path.isfile(path):
            try:
                _write_wav(path, steps)
            except OSError:
                pass
    return sfx_dir


# ------------------------------------------------------------------
# Simple frame-list animator (no pydex_ge.Animation dependency)
# ------------------------------------------------------------------

class FrameAnimator:
    """Drives a list of sprites, cycling through them by time."""

    def __init__(self, frames: list[pydex_ge.Sprite], fps: float) -> None:
        self._frames = frames
        self.interval = 1.0 / max(0.1, fps)
        self._time = 0.0
        self._index = 0

    @property
    def frames(self) -> list[pydex_ge.Sprite]:
        return self._frames

    @frames.setter
    def frames(self, value: list[pydex_ge.Sprite]) -> None:
        self._frames = value
        self._index = min(self._index, max(0, len(value) - 1))
        self._time = 0.0

    def update(self, dt: float) -> None:
        if len(self._frames) < 2:
            return
        self._time += dt
        while self._time >= self.interval:
            self._time -= self.interval
            self._index = (self._index + 1) % len(self._frames)

    @property
    def current(self) -> pydex_ge.Sprite:
        return self._frames[self._index]


# ------------------------------------------------------------------
# Entities
# ------------------------------------------------------------------

class Enemy:
    SIZE_W, SIZE_H = 56, 52

    def __init__(self, x: float, y: float, frames: list) -> None:
        self.x = x
        self.y = y
        self.anim = FrameAnimator(frames, 8)
        self.direction = 1
        self.speed = ENEMY_SPEED * random.choice((0.9, 1.0, 1.1))
        self.vy = 0.0
        self.dead = False
        self.squash = 0.0

    @property
    def rect(self) -> pydex_ge.Rect:
        return pydex_ge.Rect(self.x, self.y, self.SIZE_W, self.SIZE_H)

    def stomp(self) -> None:
        self.dead = True
        self.squash = 1e-6
        self.speed = 0.0


class CoinP:
    SIZE = 54

    def __init__(self, x: float, y: float, sprite) -> None:
        self.x = x
        self.y = y
        self.sprite = sprite
        self.timer = random.random() * 6.28

    @property
    def rect(self) -> pydex_ge.Rect:
        return pydex_ge.Rect(self.x, self.y, self.SIZE, self.SIZE)


class Pop:
    def __init__(self, x: float, y: float, text: str) -> None:
        self.x = x
        self.y = y
        self.vy = -110.0
        self.life = 0.9
        self.label = pydex_ge.Label(
            text, font=pydex_ge.Font(size=16), position=(0, 0),
            color=(255, 240, 160),
        )

    def update(self, dt: float) -> bool:
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0


# ------------------------------------------------------------------
# The game
# ------------------------------------------------------------------

class MarioGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Super (Mario-style platformer)", W, H, fps=FPS)
        self.background = SKY

        self.assets = pydex_ge.Assets()
        self.tile_sheet = self.assets.sprite_sheet(
            TILES_PATH, cell_width=TILE, cell_height=TILE
        )
        self.char_sheet = self.assets.sprite_sheet(
            CHARS_PATH, cell_width=CHAR, cell_height=CHAR
        )

        self.sfx_dir = ensure_sfx()
        self.audio = None
        try:
            self.audio = pydex_ge.Audio()
        except Exception:
            self.audio = None

        self.camera = pydex_ge.Camera(width=W, height=H, position=(W // 2, H // 2))

        # --- HUD labels ---
        self.hint = pydex_ge.Label(
            "Arrows/WASD run   Space jump   R restart   ESC quit",
            font=pydex_ge.Font(size=14), position=(12, 12), color=(16, 24, 40),
        )
        self.score_label = pydex_ge.Label(
            "SCORE 000000", font=pydex_ge.Font(size=18),
            position=(12, 44), color=(255, 255, 255),
        )
        self.coins_label = pydex_ge.Label(
            "COINS x0", font=pydex_ge.Font(size=18),
            position=(230, 44), color=(255, 220, 120),
        )
        self.time_label = pydex_ge.Label(
            "TIME 300", font=pydex_ge.Font(size=18),
            position=(520, 44), color=(255, 255, 255),
        )
        self.lives_label = pydex_ge.Label(
            "LIVES 3", font=pydex_ge.Font(size=18),
            position=(800, 44), color=(255, 255, 255),
        )
        self.banner = pydex_ge.Label(
            "", font=pydex_ge.Font(size=34),
            position=(W // 2 - 160, H // 2 - 40),
            color=(255, 224, 90), visible=False,
        )
        self.sub = pydex_ge.Label(
            "", font=pydex_ge.Font(size=18),
            position=(W // 2 - 150, H // 2 + 24),
            color=(235, 240, 255), visible=False,
        )

        self._reset_run()

    # -- sprite helpers ----------------------------------------------------

    def _tile_sprite(self, index: int) -> pydex_ge.Sprite:
        sprite = self.tile_sheet.sprite(
            index % 20 * TILE, index // 20 * TILE, TILE, TILE
        )
        sprite.scale = TILE_SCALE
        return sprite

    def _char_sprite(self, index: int) -> pydex_ge.Sprite:
        sprite = self.char_sheet.sprite(
            index % 9 * CHAR, index // 9 * CHAR, CHAR, CHAR
        )
        sprite.scale = CHAR_SCALE
        return sprite

    # -- world construction ------------------------------------------------

    def _build_world(self) -> None:
        self.level = build_level()
        self.world_w = LEVEL_COLS * CELL
        self.world_h = LEVEL_ROWS * CELL

        self.sprites: list[pydex_ge.Sprite] = []
        self.solids: list[pydex_ge.Rect] = []
        self.blocks: dict = {}
        self.block_sprite: dict = {}
        self.coins: list[CoinP] = []
        self.enemies: list[Enemy] = []
        self.pops: list[Pop] = []
        self.spawn = (2 * CELL, 11 * CELL)

        for row in range(LEVEL_ROWS):
            for col in range(LEVEL_COLS):
                kind = self.level[row][col]
                cx = col * CELL
                cy = row * CELL
                if kind == "G":
                    self._build_ground(col, row, cx, cy)
                elif kind in ("B", "?"):
                    self._build_block(row, col, cx, cy, kind)
                elif kind == "o":
                    self._build_coin(cx, cy)
                elif kind == "E":
                    self._build_enemy(cx, cy)
                elif kind == "c":
                    self._build_cloud(cx, cy)
                elif kind == "b":
                    self._build_bush(cx, cy)
                elif kind == "F":
                    self._build_flag(row, col, cx, cy)
                elif kind == "S":
                    self.spawn = (cx, cy)

        self.flag_rect = pydex_ge.Rect(
            (LEVEL_COLS - 2) * CELL, 0, CELL, LEVEL_ROWS * CELL
        )

        self._reset_player()

    def _build_ground(self, col, row, cx, cy):
        left = col == 0 or self.level[row][col - 1] != "G"
        right = col == LEVEL_COLS - 1 or self.level[row][col + 1] != "G"
        lines = ((0, 1, 2), (20, 21, 22), (40, 41, 42))
        for li, line in enumerate(lines):
            idx = line[0] if left else (line[2] if right else line[1])
            sprite = self._tile_sprite(idx)
            sprite.position = (int(cx), int(cy + li * CELL))
            self.sprites.append(sprite)
        for yy in range(3):
            self.solids.append(pydex_ge.Rect(cx, cy + yy * CELL, CELL, CELL))

    def _build_block(self, row, col, cx, cy, kind):
        if kind == "B":
            sprite = self.tile_sheet.sprite(12 * TILE, 0, 2 * TILE, 2 * TILE)
            sprite.scale = CELL / (2 * TILE)
        else:
            sprite = pydex_ge.Sprite.from_pixels(CELL, CELL, _box_pixels(True))
        sprite.position = (int(cx), int(cy))
        self.sprites.append(sprite)
        self.blocks[(row, col)] = kind
        self.block_sprite[(row, col)] = sprite
        self.solids.append(pydex_ge.Rect(cx, cy, CELL, CELL))

    def _build_coin(self, cx, cy):
        sprite = self._char_sprite(13 if random.random() < 0.5 else 14)
        sprite.position = (int(cx), int(cy))
        self.coins.append(CoinP(cx + 9, cy + 9, sprite))
        self.sprites.append(sprite)

    def _build_enemy(self, cx, cy):
        frames = [self._char_sprite(i) for i in (21, 22, 23)]
        for s in frames:
            s.scale = CHAR_SCALE * 0.9
        spawn_x = cx + (CELL - Enemy.SIZE_W) / 2
        spawn_y = cy + CELL - Enemy.SIZE_H - 4
        enemy = Enemy(spawn_x, spawn_y, frames)
        self.enemies.append(enemy)

    def _build_cloud(self, cx, cy):
        for off, idx in enumerate((154, 155)):
            sprite = self._tile_sprite(idx)
            sprite.position = (int(cx + off * CELL), int(cy))
            self.sprites.append(sprite)

    def _build_bush(self, cx, cy):
        sprite = self._tile_sprite(16)
        sprite.position = (int(cx), int(cy))
        self.sprites.append(sprite)

    def _build_flag(self, row, col, cx, cy):
        is_top = row == 0 or self.level[row - 1][col] != "F"
        sprite = self._char_sprite(24 if is_top else 25)
        sprite.position = (int(cx), int(cy))
        self.sprites.append(sprite)

    # -- player setup ------------------------------------------------------

    def _reset_player(self) -> None:
        self.pw, self.ph = 40.0, 62.0
        self.px = self.spawn[0] + (CELL - self.pw) / 2
        self.py = self.spawn[1] + CELL - self.ph
        self.vx = 0.0
        self.vy = 0.0
        self.grounded = False
        self.facing = 1
        self.invuln = INVULN_SECONDS

        # Pre-build frame sprites for each player state.
        self.player_idle = [self._char_sprite(0)]
        self.player_run = [self._char_sprite(i) for i in (1, 3, 5, 7)]
        self.player_jump = [self._char_sprite(2), self._char_sprite(4)]
        for s in self.player_idle + self.player_run + self.player_jump:
            s.scale = CHAR_SCALE
        self.player_anim = FrameAnimator(self.player_idle, 4)
        self.player_visible = True

    @property
    def player_sprite(self) -> pydex_ge.Sprite:
        return self.player_anim.current

    def _sync_player(self) -> None:
        s = self.player_sprite
        s.x = int(self.px + (self.pw - CHAR * CHAR_SCALE) / 2)
        s.y = int(self.py + (self.ph - CHAR * CHAR_SCALE))
        s.flip_x = self.facing < 0

    # -- audio & scores ----------------------------------------------------

    def _sfx(self, name: str) -> None:
        if self.audio is None:
            return
        try:
            self.audio.play_sound(os.path.join(self.sfx_dir, name + ".wav"))
        except Exception:
            pass

    def add_score(self, amount: int) -> None:
        self.score += amount
        self.score_label.text = f"SCORE {self.score:06d}"

    def _add_coin(self) -> None:
        self.coin_count += 1
        self.coins_label.text = f"COINS x{self.coin_count}"
        self.add_score(100)

    def _add_pop(self, x, y, text):
        self.pops.append(Pop(x, y, text))

    def _bump_block(self, row, col):
        key = (row, col)
        kind = self.blocks.get(key)
        if kind is None:
            return
        cx, cy = col * CELL, row * CELL
        if kind == "B":
            self.blocks[key] = ""
            self.solids.remove(pydex_ge.Rect(cx, cy, CELL, CELL))
            self.block_sprite[key].visible = False
            self.block_sprite.pop(key, None)
            self._sfx("brick")
            self.add_score(20)
            self._add_pop(cx + CELL / 2, cy, "+20")
        else:
            self.blocks[key] = ""
            self.block_sprite[key].visible = False
            new_sprite = pydex_ge.Sprite.from_pixels(CELL, CELL, _box_pixels(False))
            new_sprite.position = (int(cx), int(cy))
            self.sprites.append(new_sprite)
            self.block_sprite[key] = new_sprite
            self._sfx("coin")
            self._add_coin()
            self._add_pop(cx + CELL / 2, cy, "+100")

    # -- state -------------------------------------------------------------

    def _reset_run(self) -> None:
        self.score = 0
        self.coin_count = 0
        self.lives = START_LIVES
        self.timer = TIME_LIMIT
        self.game_over = False
        self.won = False
        self.death_timer = 0.0
        self.started = False
        self.score_label.text = f"SCORE {self.score:06d}"
        self.coins_label.text = "COINS x0"
        self.time_label.text = f"TIME {int(self.timer)}"
        self.lives_label.text = f"LIVES {self.lives}"
        self.banner.text = "SUPER PYDEX"
        self.banner.visible = True
        self.sub.text = "Press SPACE / ENTER to start"
        self.sub.visible = True
        self._build_world()

    def _die(self, *, ignore_invuln: bool = False) -> None:
        if self.death_timer > 0:
            return
        if not ignore_invuln and self.invuln > 0:
            return
        self._sfx("stomp")
        self.death_timer = 0.9
        self.player_visible = False
        self.lives -= 1
        self.lives_label.text = f"LIVES {self.lives}"
        if self.lives <= 0:
            self.lives = 0
            self.lives_label.text = "LIVES 0"

    @property
    def player_rect(self) -> pydex_ge.Rect:
        return pydex_ge.Rect(self.px, self.py, self.pw, self.ph)

    # -- frame loop --------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("escape"):
            self.close()
            return
        if self.input.is_key_pressed("r"):
            self._reset_run()
            return

        if not self.started:
            if (
                self.input.is_key_pressed("space")
                or self.input.is_key_pressed("enter")
                or self.input.is_key_pressed("up")
                or self.input.is_key_pressed("w")
            ):
                self.started = True
                self.invuln = max(self.invuln, 2.0)
                self.banner.visible = False
                self.sub.visible = False
            cam_x = max(W / 2, min(self.world_w - W / 2, self.px + self.pw / 2))
            cam_y = max(H / 2, min(self.world_h - H / 2, self.py + self.ph / 2))
            self.camera.position = (cam_x, cam_y)
            return

        if self.death_timer > 0:
            self.death_timer -= dt
            if self.death_timer <= 0:
                if self.lives <= 0:
                    self.game_over = True
                    self.banner.text = "GAME OVER"
                    self.banner.visible = True
                    self.sub.text = "Press R to restart"
                    self.sub.visible = True
                else:
                    self._reset_player()
            return

        if self.won:
            return

        if self.game_over:
            return

        self.timer -= dt
        self.time_label.text = f"TIME {int(max(0.0, self.timer))}"
        if self.timer <= 0:
            self._die(ignore_invuln=True)
            return

        self._update_player(dt)
        self._update_enemies(dt)
        self._update_coins(dt)
        self._update_pops(dt)

        self.player_anim.update(dt)
        for enemy in self.enemies:
            if not enemy.dead:
                enemy.anim.update(dt)

        if self.player_rect.overlaps(self.flag_rect):
            self.won = True
            self._sfx("oneup")
            bonus = int(self.timer) * 10
            self.add_score(bonus)
            self.banner.text = "LEVEL CLEAR!"
            self.banner.visible = True
            self.sub.text = f"Time bonus +{bonus}  Press R to replay"
            self.sub.visible = True

        cam_x = max(W / 2, min(self.world_w - W / 2, self.px + self.pw / 2))
        cam_y = max(H / 2, min(self.world_h - H / 2, self.py + self.ph / 2))
        self.camera.position = (cam_x, cam_y)

    def _update_player(self, dt):
        move = 0
        if self.input.is_key_down("left") or self.input.is_key_down("a"):
            move -= 1
            self.facing = -1
        if self.input.is_key_down("right") or self.input.is_key_down("d"):
            move += 1
            self.facing = 1

        if move != 0:
            self.vx = max(-RUN_SPEED, min(RUN_SPEED, self.vx + move * ACCEL * dt))
        elif self.grounded:
            if abs(self.vx) > 0:
                self.vx -= math.copysign(FRICTION * dt, self.vx)
                if abs(self.vx) < 1.0:
                    self.vx = 0.0
        else:
            self.vx *= 0.99

        jump_held = (
            self.input.is_key_down("space")
            or self.input.is_key_down("up")
            or self.input.is_key_down("w")
        )
        jump_pressed = (
            self.input.is_key_pressed("space")
            or self.input.is_key_pressed("up")
            or self.input.is_key_pressed("w")
        )
        if jump_pressed and self.grounded:
            self.vy = JUMP_VELOCITY
            self.grounded = False
            self._sfx("jump")
        elif not jump_held and self.vy < -400.0:
            self.vy = -400.0

        self.vy = min(self.vy + GRAVITY * dt, 1400.0)

        self.invuln = max(0.0, self.invuln - dt)

        self.px += self.vx * dt
        self.py += self.vy * dt
        landed = False
        bumped = None
        for solid in list(self.solids):
            if not self.player_rect.overlaps(solid):
                continue
            pen_left = self.player_rect.right - solid.left
            pen_right = solid.right - self.player_rect.left
            pen_top = self.player_rect.bottom - solid.top
            pen_bottom = solid.bottom - self.player_rect.top
            if min(pen_left, pen_right) < min(pen_top, pen_bottom):
                if pen_left < pen_right:
                    self.px = solid.left - self.pw
                else:
                    self.px = solid.right
                self.vx = 0.0
            elif pen_top < pen_bottom:
                self.py = solid.top - self.ph
                self.vy = 0.0
                landed = True
            else:
                self.py = solid.bottom
                self.vy = 0.0
                bumped = (int(solid.y // CELL), int(solid.x // CELL))
        if bumped is not None and bumped in self.blocks:
            self._bump_block(*bumped)
        self.grounded = landed

        self.px = max(0.0, min(self.px, self.world_w - self.pw))

        if self.py > self.world_h + 120:
            self._die(ignore_invuln=True)
            return

        if self.death_timer <= 0:
            blink = self.invuln > 0 and int(self.invuln * 14) % 2 == 0
            self.player_visible = not blink

        if not self.grounded:
            self.player_anim.frames = self.player_jump
        elif abs(self.vx) > 20.0:
            self.player_anim.frames = self.player_run
        else:
            self.player_anim.frames = self.player_idle

        self._sync_player()

    def _update_enemies(self, dt):
        for enemy in list(self.enemies):
            if enemy.squash > 0:
                enemy.squash += dt * 3.0
                if enemy.squash > 2.0:
                    self.enemies.remove(enemy)
                    continue
                progress = min(1.0, enemy.squash / 2.0)
                s = enemy.anim.current
                s.scale = (
                    CHAR_SCALE * 0.9,
                    max(0.05, CHAR_SCALE * 0.9 * (1.0 - progress)),
                )
                continue

            enemy.vy = min(enemy.vy + GRAVITY * dt, 900.0)
            enemy.y += enemy.vy * dt
            for solid in self.solids:
                if enemy.rect.overlaps(solid) and enemy.vy > 0:
                    enemy.y = solid.top - Enemy.SIZE_H
                    enemy.vy = 0.0

            enemy.x += enemy.speed * enemy.direction * dt
            front = enemy.x + (Enemy.SIZE_W if enemy.direction > 0 else 0)
            wall_probe = pydex_ge.Rect(front + 6 * enemy.direction, enemy.y + 4, 2, 10)
            if any(wall_probe.overlaps(s) for s in self.solids):
                enemy.direction *= -1
            ledge_probe = pydex_ge.Rect(
                enemy.x + enemy.SIZE_W / 2 + 14 * enemy.direction - 7,
                enemy.y + Enemy.SIZE_H + 4, 14, 8,
            )
            if not any(ledge_probe.overlaps(s) for s in self.solids):
                enemy.direction *= -1

            if self.death_timer > 0 or self.invuln > 0:
                continue
            if self.player_rect.overlaps(enemy.rect):
                if self.vy > 180.0 and self.py + self.ph - enemy.y < 30.0:
                    enemy.stomp()
                    self.vy = JUMP_VELOCITY * -0.55
                    self.grounded = False
                    self._sfx("stomp")
                    self.add_score(150)
                    self._add_pop(
                        enemy.x + Enemy.SIZE_W / 2, enemy.y, "+150"
                    )
                else:
                    self._die()

    def _update_coins(self, dt):
        for coin in list(self.coins):
            coin.timer += dt * 6.0
            coin.sprite.flip_x = int(coin.timer) % 2 == 0
            if self.player_rect.overlaps(coin.rect):
                self.coins.remove(coin)
                coin.sprite.visible = False
                self._sfx("coin")
                self._add_coin()
                self._add_pop(coin.x, coin.y, "+100")

    def _update_pops(self, dt):
        for pop in list(self.pops):
            if not pop.update(dt):
                self.pops.remove(pop)

    def _cull(self, sprite) -> bool:
        cx, cy = self.camera.x, self.camera.y
        if sprite.x > cx + W / 2 + CELL or sprite.x < cx - W / 2 - CELL:
            return True
        if sprite.y > cy + H / 2 + CELL or sprite.y < cy - H / 2 - CELL:
            return True
        return False

    def draw(self) -> None:
        self.camera.begin(self.renderer)

        # World sprites (tiles, blocks, coins, clouds, bushes, flags).
        for sprite in self.sprites:
            if sprite.visible and not self._cull(sprite):
                self.renderer.draw_sprite(sprite)

        # Enemies.
        for enemy in self.enemies:
            es = enemy.anim.current
            es.x = int(enemy.x)
            es.y = int(enemy.y)
            es.flip_x = enemy.direction < 0
            if es.visible and not self._cull(es):
                self.renderer.draw_sprite(es)

        # Player.
        if self.player_visible:
            self._sync_player()
            self.renderer.draw_sprite(self.player_sprite)

        self.camera.end()

        # Dark overlay for game-over / level-clear screens.
        if self.game_over or self.won:
            self.renderer.draw.rect(0, 0, W, H, (20, 10, 40), filled=True)

        # HUD pops (world -> screen conversion).
        for pop in self.pops:
            pop.label.position = (
                int(pop.x - self.camera.x + W / 2),
                int(pop.y - self.camera.y + H / 2),
            )
            self.renderer.draw_label(pop.label)

        if not self.game_over and not self.won and self.started:
            self.renderer.draw_label(self.hint)
        self.renderer.draw_label(self.score_label)
        self.renderer.draw_label(self.coins_label)
        self.renderer.draw_label(self.time_label)
        self.renderer.draw_label(self.lives_label)
        if self.banner.visible:
            self.renderer.draw_label(self.banner)
            self.renderer.draw_label(self.sub)


def make_game() -> pydex_ge.Game:
    return MarioGame()


def main() -> None:
    print("PYDEX Super - a Mario-style platformer (Kenney CC0 pixel art).")
    make_game().run()
    print("MarioGame closed cleanly.")


if __name__ == "__main__":
    main()
