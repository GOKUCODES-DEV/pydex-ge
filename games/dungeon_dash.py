"""PYDEX field-test: Dungeon Dash (splash screen + tile map + parallax).

Exercises ``SplashScreen`` (logo, back-ends-free loadables, min-duration
transition into the game), ``TileMap`` with a runtime-generated
``SpriteSheet`` (ground / brick / coin / goal tiles), ``Assets`` caching
shared across scenes, and ``Parallax`` background layers scrolled under a
follow camera.  The player runs across the dungeon floor, smashes bricks
by jumping into them from below, gathers coins and reaches the glowing
goal.

Controls
--------
* **Left / Right** — run
* **Space** — jump (jump straight up into a brick to smash it)
* **ESC** — quit

Run with:  python games/dungeon_dash.py
"""

from __future__ import annotations

import os
import tempfile

from _gen import blank, sheet_png, solid_pixels, stamp

import pydex_ge
from pydex_ge.physics import Rect

W, H = 800, 600
CELL = 16
COLS, ROWS = 46, 28
WORLD_W, WORLD_H = COLS * CELL, ROWS * CELL
GRAVITY = (0, 640.0)
MOVE_SPEED = 240.0
JUMP_VELOCITY = -430.0
PLAYER_W, PLAYER_H = 18, 24

# (row, start_col, length) brick platforms and coin cells (row, col).
BRICKS = (
    (21, 6, 5), (19, 12, 5), (17, 18, 6), (19, 25, 5), (17, 31, 6), (21, 38, 7),
)
COINS = (
    (20, 7), (20, 8),
    (18, 13), (18, 14),
    (16, 19), (16, 20),
    (18, 26), (18, 27),
    (16, 32), (16, 33),
    (20, 40), (20, 41),
)
GOAL = (ROWS - 3, COLS - 3)  # (row, col)


# -- level + pixel art -----------------------------------------------------


def make_level() -> list[list[str]]:
    grid = [["." for _ in range(COLS)] for _ in range(ROWS)]
    # Ground: the bottom two rows, with a low step up at the right end.
    for row in (ROWS - 2, ROWS - 1):
        for col in range(COLS):
            grid[row][col] = "G"
    # Brick walls along both edges.
    for row in range(ROWS - 2):
        grid[row][0] = "B"
        grid[row][COLS - 1] = "B"
    # Brick platforms.
    for row, col, length in BRICKS:
        for step in range(length):
            grid[row][col + step] = "B"
    # Coins float above the platforms / ground.
    for row, col in COINS:
        grid[row][col] = "C"
    grid[GOAL[0]][GOAL[1]] = "X"
    return grid


def ground_cell() -> list[list[tuple[int, int, int, int]]]:
    cell = blank(CELL)
    base = (86, 70, 58, 255)
    dark = (58, 46, 40, 255)
    light = (116, 96, 80, 255)
    for row in range(CELL):
        stamp(cell, 0, row, CELL, 1, base if row % 3 else dark)
    stamp(cell, 0, CELL - 1, CELL, 1, (108, 90, 70, 255))
    for sx, sy in ((3, 4), (10, 9), (6, 13), (12, 3), (8, 7)):
        cell[sy][sx] = light
    return cell


def brick_cell() -> list[list[tuple[int, int, int, int]]]:
    cell = blank(CELL)
    mortar = (48, 40, 36, 255)
    brick = (160, 72, 50, 255)
    dark = (128, 56, 42, 255)
    for row in range(CELL):
        stamp(cell, 0, row, CELL, 1, mortar)
    for band in (0, 4, 8, 12):
        stamp(cell, 1, band, 6, 2, brick)
        stamp(cell, 9, band, 6, 2, brick)
        stamp(cell, 1, band + 1, 5, 1, dark)
        stamp(cell, 9, band + 1, 5, 1, dark)
        stamp(cell, 1, band + 2, 7, 1, dark)
    return cell


def coin_cell() -> list[list[tuple[int, int, int, int]]]:
    cell = blank(CELL)
    gold = (255, 205, 60, 255)
    shine = (255, 240, 160, 255)
    for row in range(3, 13):
        stamp(cell, 3, row, 10, 1, gold)
    for row in range(5, 11):
        stamp(cell, 5, row, 6, 1, shine)
    stamp(cell, 7, 5, 3, 1, gold)
    return cell


def goal_cell() -> list[list[tuple[int, int, int, int]]]:
    cell = blank(CELL)
    post = (170, 150, 120, 255)
    flame = (255, 190, 60, 255)
    glow = (210, 120, 40, 255)
    stamp(cell, 7, 5, 2, 10, post)
    stamp(cell, 6, 10, 5, 1, post)
    stamp(cell, 7, 2, 2, 2, flame)
    stamp(cell, 8, 3, 1, 1, glow)
    return cell


def cloud_pixels(width: int = 160, height: int = 48) -> bytes:
    """A soft translucent cloud band (staggered ellipses) for parallax."""
    pixels = bytearray(width * height * 4)
    base = 26
    for row in range(height):
        for col in range(width):
            shape = max(0.0, (14 - abs(((col - 32) % 96) - 48)) * 0.55)
            center = base - shape
            dy = abs(row - center)
            alpha = max(0, int(90 - dy * 7)) if dy < 15 else 0
            index = (row * width + col) * 4
            pixels[index:index + 4] = bytes((232, 240, 255, min(255, alpha)))
    return bytes(pixels)


def badge_pixels(size: int = 120) -> bytes:
    """A round ring badge with a letter gap (used as the splash logo)."""
    pixels = bytearray(size * size * 4)
    center = size // 2
    radius = size // 2 - 4
    for row in range(size):
        for col in range(size):
            dx, dy = col - center, row - center
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= radius:
                color = (70, 120, 220, 255) if dist > radius * 0.72 else (92, 150, 240, 255)
            elif dist <= radius + 3:
                color = (255, 210, 60, 255)
            else:
                color = (0, 0, 0, 0)
            index = (row * size + col) * 4
            pixels[index:index + 4] = bytes(color)
    # Letter gap: a rounded rectangle cut across the ring.
    gap_top, gap_bottom = int(size * 0.24), int(size * 0.62)
    for row in range(gap_top, gap_bottom):
        for col in range(int(size * 0.20), int(size * 0.44)):
            index = (row * size + col) * 4
            pixels[index:index + 4] = bytes((0, 0, 0, 0))
    return bytes(pixels)


# -- scenes ----------------------------------------------------------------


class TileLayer:
    """Draws the TileMap; used so the whole grid has a low ``z``."""

    z = -10

    def __init__(self, tilemap) -> None:
        self.tilemap = tilemap

    def draw(self, renderer) -> None:
        self.tilemap.render(renderer)


class DungeonScene(pydex_ge.Scene):
    """Run and jump through the dungeon gathering coins."""

    def __init__(self, game, assets, sheet_path) -> None:
        super().__init__(camera=pydex_ge.Camera2D(W, H, position=(W // 2, H // 2)))
        self.game = game
        self.sheet = assets.sprite_sheet(sheet_path, CELL, CELL)

        # -- grid ------------------------------------------------------
        self.tilemap = pydex_ge.TileMap(COLS, ROWS, tile_size=(CELL, CELL), sprite_sheet=self.sheet)
        icons = {".": 0, "G": 1, "B": 2, "C": 3, "X": 4}
        grid = make_level()
        self.coin_cells: list[tuple[int, int]] = []
        for row in range(ROWS):
            for col in range(COLS):
                tile_id = icons[grid[row][col]]
                if tile_id:
                    self.tilemap.set_tile(col, row, tile_id)
                    if tile_id == 3:
                        self.coin_cells.append((col, row))
        self.tilemap.set_solid(1, True)  # ground
        self.tilemap.set_solid(2, True)  # brick

        # -- physics ----------------------------------------------------
        self.world = pydex_ge.World(
            gravity=GRAVITY, static_rects=tuple(self.tilemap.solid_rects())
        )
        self.body = pydex_ge.Body(
            position=(3 * CELL, WORLD_H - 2 * CELL - PLAYER_H),
            size=(PLAYER_W, PLAYER_H),
        )
        self.world.add_body(self.body)

        self.player = pydex_ge.Sprite.from_pixels(
            PLAYER_W, PLAYER_H, solid_pixels(PLAYER_W, PLAYER_H, (240, 210, 130))
        )
        self.player.z = 2

        # -- parallax clouds --------------------------------------------
        for cx, cy, factor in (
            (30, 40, 0.30), (300, 30, 0.45), (560, 80, 0.35), (740, 45, 0.50),
        ):
            cloud = pydex_ge.Sprite.from_pixels(160, 48, cloud_pixels())
            cloud.position = (cx, cy)
            self.add(pydex_ge.Parallax(cloud, factor=factor))

        # -- camera & HUD ------------------------------------------------
        self.camera.bounds = Rect(0, 0, WORLD_W, WORLD_H)
        self.camera.follow(self.body, smoothing=3.0)

        self.coins_label = pydex_ge.Label(
            f"Coins: {len(self.coin_cells)}", font=pydex_ge.Font(size=16),
            position=(12, 12), color=(255, 220, 120),
        )
        self.hint_label = pydex_ge.Label(
            "Arrows: move   Space: jump (smash bricks!)   ESC: quit",
            font=pydex_ge.Font(size=14), position=(12, 36), color=(150, 160, 185),
        )

        self.add(TileLayer(self.tilemap))
        self.add(self.player)
        self.add(self.coins_label)
        self.add(self.hint_label)

        self.won = False

    def _rebuild_static(self) -> None:
        self.world.static_rects = tuple(self.tilemap.solid_rects())

    def update(self, dt: float) -> None:
        dx = 0.0
        if self.game.input.is_key_down("left"):
            dx -= MOVE_SPEED
        if self.game.input.is_key_down("right"):
            dx += MOVE_SPEED
        self.body.velocity = (dx, self.body.velocity.y)

        grounded = self.body.velocity.y == 0 and any(
            self.body.collides_with(rect) for rect in self.world.static_rects
        )
        if self.game.input.is_key_pressed("space") and grounded:
            self.body.apply_impulse((0, JUMP_VELOCITY))

        # Capture "rising" *before* physics: the collision solver zeroes the
        # upward velocity when the head hits a brick, which would otherwise
        # hide the smash.
        rising = self.body.velocity.y < 0

        self.world.update(dt)
        self.body.position = (
            max(0.0, min(self.body.position.x, WORLD_W - PLAYER_W)),
            self.body.position.y,
        )
        self.camera.update(dt)
        self.player.position = (int(self.body.position.x), int(self.body.position.y))

        if self.game.input.is_key_pressed("escape"):
            self.game.close()
            return

        # Smash bricks from below: rising into a brick tile clears it.
        if rising:
            x0 = int(self.body.position.x // CELL)
            x1 = int((self.body.position.x + PLAYER_W - 1) // CELL)
            y0 = max(0, int((self.body.position.y - 2) // CELL))
            y1 = int(self.body.position.y // CELL)
            smashed = False
            for row in range(y0, y1 + 1):
                for col in range(x0, x1 + 1):
                    if row < ROWS and self.tilemap.get_tile(col, row) == 2:
                        self.tilemap.set_tile(col, row, 0)
                        smashed = True
            if smashed:
                self._rebuild_static()
                print("[dungeon] brick smashed")

        # Collect coin tiles the body overlaps.
        kept: list[tuple[int, int]] = []
        for col, row in self.coin_cells:
            coin_rect = Rect(col * CELL, row * CELL, CELL, CELL)
            if self.body.rect.overlaps(coin_rect):
                self.tilemap.set_tile(col, row, 0)
                print("[dungeon] coin collected")
            else:
                kept.append((col, row))
        self.coin_cells = kept
        self.coins_label.text = f"Coins: {len(self.coin_cells)}"

        # Reaching the goal tile wins the level.
        goal_rect = Rect(GOAL[1] * CELL, GOAL[0] * CELL, CELL, CELL)
        if not self.won and self.body.rect.overlaps(goal_rect):
            self.won = True
            message = "All coins gathered - the dungeon is yours!"
            if self.coin_cells:
                message = "Goal reached! (some coins remain)"
            self.manager.replace(GameOverScene(self.game, self.sheet_path, message))

    @property
    def sheet_path(self) -> str:
        return self.game.sheet_path


class GameOverScene(pydex_ge.Scene):
    """Result screen; SPACE/ENTER replays, ESC quits."""

    def __init__(self, game, sheet_path: str, message: str) -> None:
        super().__init__()
        self.game = game
        self.sheet_path = sheet_path
        self.add(pydex_ge.Label(
            message, font=pydex_ge.Font(size=20), position=(W // 2 - 230, H // 2 - 40),
            color=(255, 210, 90),
        ))
        self.add(pydex_ge.Label(
            "SPACE: play again   ESC: quit", font=pydex_ge.Font(size=15),
            position=(W // 2 - 130, H // 2 + 20), color=(150, 160, 185),
        ))

    def update(self, dt: float) -> None:
        if self.game.input.is_key_pressed("space") or self.game.input.is_key_pressed("return"):
            self.manager.replace(DungeonScene(self.game, self.game.assets, self.sheet_path))
        elif self.game.input.is_key_pressed("escape"):
            self.game.close()


class DungeonGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Dungeon Dash", W, H, fps=60)
        self.background = (24, 20, 30)

        self.assets = pydex_ge.Assets()
        self._tmp = tempfile.TemporaryDirectory()
        self.sheet_path = os.path.join(self._tmp.name, "dungeon_tiles.png")
        with open(self.sheet_path, "wb") as handle:
            handle.write(sheet_png(
                [ground_cell(), brick_cell(), coin_cell(), goal_cell()], size=CELL
            ))

        logo = pydex_ge.Sprite.from_pixels(120, 120, badge_pixels())
        self.scenes.push(pydex_ge.SplashScreen(
            logo=logo,
            name="PYDEX Dungeon Dash",
            version="0.1",
            loading_speed=2.0,
            loadables=[("sprite_sheet", self.sheet_path, CELL, CELL)],
            assets=self.assets,
            next_scene=lambda: DungeonScene(self, self.assets, self.sheet_path),
            game=self,
            min_duration=1.2,
        ))

    def close(self) -> None:
        self.assets.clear()
        self._tmp.cleanup()
        super().close()


def make_game() -> pydex_ge.Game:
    return DungeonGame()


def main() -> None:
    print("PYDEX Dungeon Dash - run, jump, smash bricks, grab the coins and the goal.")
    make_game().run()
    print("DungeonGame closed cleanly.")


if __name__ == "__main__":
    main()