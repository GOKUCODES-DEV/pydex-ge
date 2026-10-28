"""PYDEX Part 9 example: Scenes + SceneManager + Assets caching.

Three scenes run on top of a :class:`pydex_ge.SceneManager` stack:

* **Menu** — the base scene.  Press SPACE to push the Game scene on top.
* **Game** — a camera-followed player walks around a world collecting coins;
  the world is drawn through a :class:`pydex_ge.Camera`.  Press ``A`` to push
  the Asset scene, ESC pops back to the menu.
* **Assets** — an overlay proving the asset cache returns the *same*
  objects for repeated loads.  ESC pops back to the game.

Pushing suspends the scene below it; popping resumes the revealed scene
without re-entering it.  Every transition prints to the console so the
lifecycle is visible.

Controls: Arrow keys move, SPACE starts, A opens the asset scene,
ESC goes back / quits.  The example also closes itself after ~50 seconds.

Run with:  python examples/scenes.py
"""

from __future__ import annotations

import struct
import tempfile

import pydex_ge
from pydex_ge.physics import Rect

CELL = 16
WORLD_W, WORLD_H = 1200, 800
SPEED = 220.0


# -- tiny runtime PNG generator (standard library only) ------------------


def _png_bytes(width: int, height: int, rows: list[bytes]) -> bytes:
    """Encode RGBA rows (top-down, ``width * 4`` bytes each) as a PNG."""
    import zlib

    def _chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    scanlines = b"".join(b"\x00" + row for row in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(scanlines))
        + _chunk(b"IEND", b"")
    )


def _blank(size: int) -> list[list[tuple[int, int, int, int]]]:
    return [[(0, 0, 0, 0)] * size for _ in range(size)]


def _stamp(cell, x: int, y: int, w: int, h: int, color) -> None:
    for row in range(y, y + h):
        for col in range(x, x + w):
            if 0 <= row < len(cell) and 0 <= col < len(cell[0]):
                cell[row][col] = color


def _player_frames() -> list[list[list[tuple[int, int, int, int]]]]:
    skin = (245, 210, 170, 255)
    hair = (70, 70, 95, 255)
    shirt = (80, 160, 255, 255)
    sleeve = (60, 130, 220, 255)
    pants = (45, 60, 90, 255)
    boot = (30, 30, 45, 255)
    eye = (20, 20, 20, 255)

    def make(leg_l, leg_r, arm_l, arm_r):
        cell = _blank(CELL)
        _stamp(cell, 6, 2, 4, 3, skin)
        _stamp(cell, 6, 1, 4, 2, hair)
        _stamp(cell, 7, 3, 1, 1, eye)
        _stamp(cell, 9, 3, 1, 1, eye)
        _stamp(cell, 5, 5, 6, 6, shirt)
        for ax, ay in (arm_l, arm_r):
            _stamp(cell, ax, ay, 2, 5, sleeve)
        for lx, ly in (leg_l, leg_r):
            _stamp(cell, lx, ly, 2, 5, pants)
        _stamp(cell, leg_l[0], leg_l[1] + 5, 2, 2, boot)
        _stamp(cell, leg_r[0], leg_r[1] + 5, 2, 2, boot)
        return cell

    return [
        make((6, 10), (9, 10), (3, 6), (11, 6)),
        make((5, 10), (10, 9), (3, 5), (11, 6)),
        make((6, 10), (9, 10), (3, 6), (11, 6)),
        make((10, 9), (5, 10), (11, 5), (3, 6)),
    ]


def _coin_cell() -> list[list[tuple[int, int, int, int]]]:
    cell = _blank(CELL)
    gold = (255, 210, 60, 255)
    shine = (255, 235, 150, 255)
    for row in range(2, 14):
        _stamp(cell, 2, row, 12, 1, gold)
    for row in range(4, 12):
        _stamp(cell, 4, row, 8, 1, shine)
    _stamp(cell, 6, 5, 4, 1, gold)
    return cell


def _ground_cell() -> list[list[tuple[int, int, int, int]]]:
    cell = _blank(CELL)
    green = (62, 120, 72, 255)
    dark = (48, 96, 58, 255)
    speck = (74, 140, 84, 255)
    for row in range(CELL):
        _stamp(cell, 0, row, CELL, 1, green)
    for row in range(CELL):
        cell[row][0] = dark
        cell[row][CELL - 1] = dark
    cell[0] = [dark] * CELL
    cell[CELL - 1] = [dark] * CELL
    for sx, sy in ((5, 5), (11, 10), (8, 2)):
        cell[sy][sx] = speck
    return cell


def _cell_rows(cell) -> list[bytes]:
    rows: list[bytes] = []
    for row in range(len(cell)):
        line = bytearray()
        for col in range(len(cell[row])):
            line += bytes(cell[row][col])
        rows.append(bytes(line))
    return rows


def _sheet_bytes(frames) -> bytes:
    rows: list[bytes] = []
    for row in range(CELL):
        line = bytearray()
        for frame in frames:
            for col in range(CELL):
                line += bytes(frame[row][col])
        rows.append(bytes(line))
    return _png_bytes(CELL * len(frames), CELL, rows)


def _solid_bytes(width: int, height: int, color) -> bytes:
    row = bytes((*color, 255)) * width
    return row * height


# -- scenes --------------------------------------------------------------


class MenuScene(pydex_ge.Scene):
    """Base scene: title screen that pushes the Game scene on SPACE."""

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        title = pydex_ge.Font(size=40)
        normal = pydex_ge.Font(size=18)
        small = pydex_ge.Font(size=14)
        self.add(pydex_ge.Label("PYDEX Scenes", font=title, position=(250, 200), color=(255, 255, 255)))
        self.add(pydex_ge.Label("A scene-stack demo", font=normal, position=(310, 265), color=(180, 200, 220)))
        self.add(pydex_ge.Label("SPACE: start the game", font=normal, position=(270, 330), color=(255, 210, 90)))
        self.add(pydex_ge.Label("ESC: quit", font=small, position=(355, 370), color=(150, 160, 180)))

    def on_enter(self) -> None:
        print("[menu] entered")

    def on_exit(self) -> None:
        print("[menu] exited (suspended by a scene above it)")

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.game.input.is_key_pressed("space"):
            self.manager.push(GameScene(self.game))


class GameScene(pydex_ge.Scene):
    """Main gameplay: camera-followed player collects coins."""

    def __init__(self, game) -> None:
        super().__init__(camera=pydex_ge.Camera2D(800, 600, position=(400, 400)))
        self.game = game
        assets = game.assets

        self.floor = pydex_ge.Sprite.from_pixels(
            WORLD_W, WORLD_H, _solid_bytes(WORLD_W, WORLD_H, (30, 70, 42))
        )
        self.floor.position = (0, 0)

        sheet = assets.sprite_sheet(game.player_sheet_path, CELL, CELL)
        self.player = pydex_ge.Sprite(sheet.image)
        self.player.position = (400, 400)
        self.player.animations["idle"] = sheet.animation([(0, 0)], fps=2, loop=True)
        self.player.animations["walk"] = sheet.animation_run(0, 0, 4, fps=10, loop=True)
        self.player.play_animation("idle")

        self.coins = []
        for x, y in ((250, 250), (700, 420), (950, 620), (480, 700)):
            coin = pydex_ge.Sprite(assets.image(game.coin_path))
            coin.position = (x, y)
            self.coins.append(coin)

        self.camera.bounds = Rect(0, 0, WORLD_W, WORLD_H)
        self.camera.follow(self.player, smoothing=4.0)

        self.coins_left = pydex_ge.Label("Coins: 4", font=pydex_ge.Font(size=16), position=(12, 12), color=(255, 220, 120))
        self.hint = pydex_ge.Label(
            "Arrows: move    A: asset scene    ESC: menu",
            font=pydex_ge.Font(size=14),
            position=(12, 36),
            color=(150, 160, 185),
        )
        self.add(self.player)
        self.add(self.coins_left)
        self.add(self.hint)

    def on_enter(self) -> None:
        print("[game] entered")

    def on_exit(self) -> None:
        print("[game] exited")

    def update(self, dt: float) -> None:
        super().update(dt)

        moving = False
        if self.game.input.is_key_down("left"):
            self.player.x -= int(SPEED * dt)
            moving = True
        if self.game.input.is_key_down("right"):
            self.player.x += int(SPEED * dt)
            moving = True
        if self.game.input.is_key_down("up"):
            self.player.y -= int(SPEED * dt)
            moving = True
        if self.game.input.is_key_down("down"):
            self.player.y += int(SPEED * dt)
            moving = True
        self.player.x = max(0, min(self.player.x, WORLD_W - CELL))
        self.player.y = max(0, min(self.player.y, WORLD_H - CELL))
        self.player.play_animation("walk" if moving else "idle")
        self.camera.update(dt)

        kept = []
        for coin in self.coins:
            if (
                coin.x < self.player.x + CELL
                and coin.x + CELL > self.player.x
                and coin.y < self.player.y + CELL
                and coin.y + CELL > self.player.y
            ):
                print(f"[game] coin collected at ({coin.x},{coin.y})")
            else:
                kept.append(coin)
        self.coins = kept
        self.coins_left.text = f"Coins: {len(self.coins)}"

        if self.game.input.is_key_pressed("a"):
            self.manager.push(AssetScene(self.game, self))
        elif self.game.input.is_key_pressed("escape"):
            self.manager.pop()

    def draw(self, renderer) -> None:
        self.camera.begin(renderer)
        renderer.draw_sprite(self.floor)
        for coin in self.coins:
            coin.draw(renderer)
        self.player.draw(renderer)
        self.camera.end()
        renderer.draw_label(self.coins_left)
        renderer.draw_label(self.hint)


class AssetScene(pydex_ge.Scene):
    """Overlay demonstrating the asset cache returns the same objects."""

    def __init__(self, game, back: pydex_ge.Scene) -> None:
        super().__init__()
        self.game = game
        self.back = back
        font = pydex_ge.Font(size=15)

        self.panel = pydex_ge.Sprite.from_pixels(560, 250, _solid_bytes(560, 250, (30, 34, 48)))
        self.panel.position = (120, 170)

        assets = game.assets
        same_image = assets.image(game.coin_path) is assets.image(game.coin_path)
        same_sheet = assets.sprite_sheet(game.player_sheet_path, CELL, CELL) is assets.sprite_sheet(
            game.player_sheet_path, CELL, CELL
        )
        sheet_reuses = assets.sprite_sheet(game.player_sheet_path, CELL, CELL).image is assets.image(
            game.player_sheet_path
        )
        lines = [
            f"same image object:  {same_image}",
            f"same sheet object:  {same_sheet}",
            f"sheet reuses image: {sheet_reuses}",
            f"cached assets:      {len(assets)} (2 images + 1 sheet)",
        ]
        self.lines = [
            pydex_ge.Label(text, font=font, position=(160, 195 + index * 26), color=(200, 215, 235))
            for index, text in enumerate(lines)
        ]
        self.footer = pydex_ge.Label(
            "Every load returned the cached instance.",
            font=font,
            position=(160, 310),
            color=(255, 210, 90),
        )
        self.hint = pydex_ge.Label(
            "ESC: back to the game", font=font, position=(160, 340), color=(150, 160, 185)
        )

    def on_enter(self) -> None:
        print("[assets] entered")

    def on_exit(self) -> None:
        print("[assets] exited")

    def update(self, dt: float) -> None:
        if self.game.input.is_key_pressed("escape"):
            self.manager.pop()

    def draw(self, renderer) -> None:
        renderer.draw_sprite(self.panel)
        for line in self.lines:
            renderer.draw_label(line)
        renderer.draw_label(self.footer)
        renderer.draw_label(self.hint)


# -- application ---------------------------------------------------------


class ScenesDemo(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Scenes + Assets", 800, 600, fps=60)
        self.background = (22, 24, 34)
        self._elapsed = 0.0

        self.assets = pydex_ge.Assets()
        self._tmp = tempfile.TemporaryDirectory()

        self.player_sheet_path = f"{self._tmp.name}/player.png"
        with open(self.player_sheet_path, "wb") as handle:
            handle.write(_sheet_bytes(_player_frames()))
        self.coin_path = f"{self._tmp.name}/coin.png"
        with open(self.coin_path, "wb") as handle:
            handle.write(_png_bytes(CELL, CELL, _cell_rows(_coin_cell())))

        self.scenes.push(MenuScene(self))

    def update(self, dt: float) -> None:
        self._elapsed += dt
        if self._elapsed > 50.0:
            print("Demo complete - closing window.")
            self.close()

    def close(self) -> None:
        self.assets.clear()
        super().close()


def main() -> None:
    print(
        "PYDEX scenes + assets example.\n"
        "SPACE starts the game, arrows move, A opens the asset overlay, "
        "ESC goes back / quits."
    )
    game = ScenesDemo()
    game.run()
    print("ScenesDemo closed cleanly.")


if __name__ == "__main__":
    main()
