"""Temporary manual test for Part 9: Scenes + Asset Management.

Walks the Part 9 features through a small scene-stack game:

* **Main scene** is the base of the stack.
  * ``G`` -> ``replace(GameScene)`` (full transition: main exits, game enters).
  * ``A`` -> ``push(AssetScene)`` overlay (main is suspended, not exited).
  * ``P`` -> ``push(PauseScene)`` overlay (same suspension behaviour).
  * ``ESC`` -> quit.
* **Game scene** has a camera-followed player that moves with the arrows and
  collects coins.
  * ``M`` / ``ESC`` -> ``replace(MainScene)`` (back with replace()).
  * ``A`` / ``P`` -> push the Asset / Pause overlays.
* **Asset overlay** proves the cache returns identical objects for images,
  fonts, and sprite sheets, and that a sheet reuses the cached image.
* **Pause overlay** proves the game scene below is suspended: only the
  overlay's own counter advances while it is current.

Every ``on_enter()``/``on_exit()`` prints to the console and to an on-screen
log so the lifecycle, suspension, and resume behaviour is visible.

Run modes::

    python examples/manual_scenes_assets_test.py --check   # headless scene/manager/assets checks
    python examples/manual_scenes_assets_test.py --demo    # auto-driven windowed run
    python examples/manual_scenes_assets_test.py           # interactive windowed run

The interactive run keeps the window open until ESC is pressed.

This file is a manual verification aid only; it is not part of the public
PYDEX API and may be deleted at any time.
"""

from __future__ import annotations

import os
import shutil
import struct
import sys
import tempfile

import pydex_ge
from pydex_ge.backend.null import NullBackend

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


def _find_font_path() -> str | None:
    """Locate a real system TTF so the font cache can be exercised with SDL2."""
    if sys.platform.startswith("win"):
        fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        for name in ("arial.ttf", "segoeui.ttf", "tahoma.ttf", "calibri.ttf", "consola.ttf"):
            path = os.path.join(fonts, name)
            if os.path.isfile(path):
                return path
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if os.path.isfile(path):
            return path
    return None


# -- shared HUD ----------------------------------------------------------


class Hud:
    """Reusable on-screen HUD: title, controls, status lines, transition log."""

    def __init__(self, game, title: str, controls: str) -> None:
        self._game = game
        self._title = pydex_ge.Label("", font=game.font_title, position=(12, 8), color=(255, 255, 255))
        self._controls = pydex_ge.Label(
            "", font=game.font_small, position=(12, 36), color=(160, 175, 200)
        )
        self._lines = [
            pydex_ge.Label("", font=game.font_small, position=(12, 60 + i * 18), color=(220, 230, 245))
            for i in range(4)
        ]
        self._log = [
            pydex_ge.Label("", font=game.font_tiny, position=(12, 140 + i * 15), color=(140, 150, 170))
            for i in range(4)
        ]
        self._title.text = title
        self._controls.text = controls

    def render(self, renderer, lines, log) -> None:
        for i, label in enumerate(self._lines):
            label.text = lines[i] if i < len(lines) else ""
        for i, label in enumerate(self._log):
            label.text = log[i] if i < len(log) else ""
        for label in (self._title, self._controls, *self._lines, *self._log):
            renderer.draw_label(label)


# -- scenes --------------------------------------------------------------


class MainScene(pydex_ge.Scene):
    title = "MAIN SCENE (base of the stack)"

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.hud = Hud(
            game,
            self.title,
            "G: replace -> Game    A: push Asset    P: push Pause    ESC: quit",
        )

    def on_enter(self) -> None:
        self.game.record("MainScene: on_enter")

    def on_exit(self) -> None:
        self.game.record("MainScene: on_exit")

    def update(self, dt: float) -> None:
        if self.game.key_pressed("g"):
            self.manager.replace(self.game.game_scene)
        elif self.game.key_pressed("a"):
            self.manager.push(self.game.asset_scene)
        elif self.game.key_pressed("p"):
            self.manager.push(self.game.pause_scene)
        elif self.game.key_pressed("escape"):
            self.game.close()

    def draw(self, renderer) -> None:
        self.hud.render(
            renderer,
            [
                f"stack: {self.game.stack_text()}",
                "push suspends the scenes below without exiting them",
                "replace() fully transitions (old exits, new enters)",
                f"log tail: {self.game.log[-1] if self.game.log else '-'}",
            ],
            self.game.log[-4:],
        )


class GameScene(pydex_ge.Scene):
    title = "GAME SCENE (camera follow + coins)"

    def __init__(self, game) -> None:
        super().__init__(camera=pydex_ge.Camera2D(800, 600, position=(400, 400)))
        self.game = game
        self.hud = Hud(
            game,
            self.title,
            "arrows: move    A: push Asset    P: push Pause    M / ESC: replace -> Main",
        )

        self.floor = pydex_ge.Sprite.from_pixels(
            WORLD_W, WORLD_H, _solid_bytes(WORLD_W, WORLD_H, (30, 70, 42))
        )
        self.floor.position = (0, 0)

        sheet = game.assets.sprite_sheet(game.player_sheet_path, CELL, CELL)
        self.player = pydex_ge.Sprite(sheet.image)
        self.player.position = (400, 400)
        self.player.animations["idle"] = sheet.animation([(0, 0)], fps=2, loop=True)
        self.player.animations["walk"] = sheet.animation_run(0, 0, 4, fps=10, loop=True)
        self.player.play_animation("idle")
        self.add(self.player)

        self.coins = []
        for x, y in ((250, 250), (700, 420), (950, 620), (480, 700)):
            coin = pydex_ge.Sprite(game.assets.image(game.coin_path))
            coin.position = (x, y)
            self.coins.append(coin)

        self.camera.bounds = pydex_ge.Rect(0, 0, WORLD_W, WORLD_H)
        self.camera.follow(self.player, smoothing=4.0)

    def on_enter(self) -> None:
        self.game.record("GameScene: on_enter")

    def on_exit(self) -> None:
        self.game.record("GameScene: on_exit")

    def update(self, dt: float) -> None:
        super().update(dt)

        moving = False
        if self.game.key_down("left"):
            self.player.x -= int(SPEED * dt)
            moving = True
        if self.game.key_down("right"):
            self.player.x += int(SPEED * dt)
            moving = True
        if self.game.key_down("up"):
            self.player.y -= int(SPEED * dt)
            moving = True
        if self.game.key_down("down"):
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
                self.game.record(f"coin collected at ({coin.x},{coin.y})")
            else:
                kept.append(coin)
        self.coins = kept

        if self.game.key_pressed("a"):
            self.manager.push(self.game.asset_scene)
        elif self.game.key_pressed("p"):
            self.manager.push(self.game.pause_scene)
        elif self.game.key_pressed("m") or self.game.key_pressed("escape"):
            self.manager.replace(self.game.main_scene)

    def draw(self, renderer) -> None:
        self.camera.begin(renderer)
        renderer.draw_sprite(self.floor)
        for coin in self.coins:
            coin.draw(renderer)
        self.player.draw(renderer)
        self.camera.end()

        cam = self.camera
        player = self.player
        offset = (player.x - cam.x, player.y - cam.y)
        self.hud.render(
            renderer,
            [
                f"player ({player.x},{player.y})  cam ({cam.x:.0f},{cam.y:.0f})  "
                f"offset ({offset[0]:.0f},{offset[1]:.0f})",
                f"zoom {cam.zoom:.2f}  coins left {len(self.coins)}  "
                f"stack: {self.game.stack_text()}",
                "player added to the scene: scene.update(dt) advances its animation",
                "state persists across scene switches (position kept)",
            ],
            self.game.log[-4:],
        )


class AssetScene(pydex_ge.Scene):
    title = "ASSET SCENE (cache overlay, pushed on top)"

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.hud = Hud(game, self.title, "ESC: pop -> back to the scene below")

        self.panel = pydex_ge.Sprite.from_pixels(560, 340, _solid_bytes(560, 340, (30, 34, 48)))
        self.panel.position = (120, 130)

        self.coin_preview = pydex_ge.Sprite(game.assets.image(game.coin_path))
        self.coin_preview.position = (170, 320)
        sheet = game.assets.sprite_sheet(game.player_sheet_path, CELL, CELL)
        self.player_preview = sheet.cell(0, 0)
        self.player_preview.position = (230, 320)

        font = game.font_small
        self.labels = [
            pydex_ge.Label("", font=font, position=(160, 170 + i * 22), color=(200, 215, 235))
            for i in range(6)
        ]

    def on_enter(self) -> None:
        self.game.record("AssetScene: on_enter")

    def on_exit(self) -> None:
        self.game.record("AssetScene: on_exit")

    def update(self, dt: float) -> None:
        if self.game.key_pressed("escape"):
            self.manager.pop()

    def draw(self, renderer) -> None:
        assets = self.game.assets
        img = assets.image(self.game.coin_path)
        sheet = assets.sprite_sheet(self.game.player_sheet_path, CELL, CELL)
        font_same = "-"
        if self.game.font_path:
            font_same = str(assets.font(self.game.font_path, 16) is assets.font(self.game.font_path, 16))
        lines = [
            f"len(assets) = {len(assets)}   (coin image + player image + sheet + font)",
            f"image loads return the same object: {img is assets.image(self.game.coin_path)}",
            f"font  loads return the same object: {font_same}",
            f"sheet loads return the same object: {sheet is assets.sprite_sheet(self.game.player_sheet_path, CELL, CELL)}",
            f"sheet.image is assets.image(path): {sheet.image is assets.image(self.game.player_sheet_path)}",
            f"stack: {self.game.stack_text()}",
        ]
        for i, label in enumerate(self.labels):
            label.text = lines[i]

        renderer.draw_sprite(self.panel)
        self.coin_preview.draw(renderer)
        self.player_preview.draw(renderer)
        for label in self.labels:
            renderer.draw_label(label)
        self.hud.render(renderer, [], self.game.log[-4:])


class PauseScene(pydex_ge.Scene):
    title = "PAUSE SCENE (overlay: the scene below is suspended)"

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.hud = Hud(game, self.title, "ESC: pop -> resume the scene below")
        self.panel = pydex_ge.Sprite.from_pixels(560, 200, _solid_bytes(560, 200, (28, 30, 40)))
        self.panel.position = (120, 150)
        self.tick = 0
        self.labels = [
            pydex_ge.Label("", font=game.font_small, position=(160, 180 + i * 22), color=(200, 215, 235))
            for i in range(3)
        ]

    def on_enter(self) -> None:
        self.game.record("PauseScene: on_enter")

    def on_exit(self) -> None:
        self.game.record("PauseScene: on_exit")

    def update(self, dt: float) -> None:
        self.tick += 1
        if self.game.key_pressed("escape"):
            self.manager.pop()

    def draw(self, renderer) -> None:
        below = self.game.scenes.current is self
        lines = [
            f"pause tick {self.tick}  (only this overlay advances while it is current)",
            f"game scene suspended: its update()/draw() are NOT called below",
            f"stack: {self.game.stack_text()}   current is self: {below}",
        ]
        for i, label in enumerate(self.labels):
            label.text = lines[i]
        renderer.draw_sprite(self.panel)
        for label in self.labels:
            renderer.draw_label(label)
        self.hud.render(renderer, [], self.game.log[-4:])


# -- application ---------------------------------------------------------


class ManualPart9Game(pydex_ge.Game):
    def __init__(self, demo: bool = False) -> None:
        super().__init__("PYDEX Part 9 manual test", 800, 600, fps=60)
        self.demo = demo
        self.background = (18, 18, 26)
        self.log: list[str] = []
        self._elapsed = 0.0
        self._demo_last_t = 0.0
        self._demo_held: set[str] = set()
        self._demo_pressed: set[str] = set()

        self.font_title = pydex_ge.Font(size=22)
        self.font_small = pydex_ge.Font(size=15)
        self.font_tiny = pydex_ge.Font(size=12)

        self.assets = pydex_ge.Assets()
        self._tmp = tempfile.TemporaryDirectory()

        self.player_sheet_path = f"{self._tmp.name}/player.png"
        with open(self.player_sheet_path, "wb") as handle:
            handle.write(_sheet_bytes(_player_frames()))
        self.coin_path = f"{self._tmp.name}/coin.png"
        with open(self.coin_path, "wb") as handle:
            handle.write(_png_bytes(CELL, CELL, _cell_rows(_coin_cell())))

        system_font = _find_font_path()
        self.font_path: str | None = None
        if system_font is not None:
            self.font_path = f"{self._tmp.name}/ui_font.ttf"
            shutil.copyfile(system_font, self.font_path)

        self.main_scene = MainScene(self)
        self.game_scene = GameScene(self)
        self.asset_scene = AssetScene(self)
        self.pause_scene = PauseScene(self)
        self.scenes.push(self.main_scene)

        print("PYDEX Part 9 manual test.")
        print(
            "Controls: G replace->Game, M/ESC replace->Main, A push Asset, "
            "P push Pause, ESC in overlays pops, ESC in Main quits."
        )
        print("Demo mode on." if demo else "Interactive mode.")

    # -- helpers ---------------------------------------------------------

    def record(self, message: str) -> None:
        self.log.append(message)
        if len(self.log) > 12:
            del self.log[: len(self.log) - 12]
        print("[scene] " + message, flush=True)

    def stack_text(self) -> str:
        names = [scene.title for scene in self.scenes]
        current = self.scenes.current.title if self.scenes.current else "none"
        return " > ".join(names) + f"  [current: {current}]"

    def key_down(self, name: str) -> bool:
        if self.demo:
            return name in self._demo_held
        return self.input.is_key_down(name)

    def key_pressed(self, name: str) -> bool:
        if self.demo:
            return name in self._demo_pressed
        return self.input.is_key_pressed(name)

    # -- demo driver -----------------------------------------------------

    _DEMO_EVENTS = (
        (1.5, "g"),
        (5.5, "a"),
        (7.0, "escape"),
        (8.5, "p"),
        (9.5, "escape"),
        (12.0, "escape"),
        (13.5, "a"),
        (14.5, "escape"),
    )

    def _demo_step(self) -> None:
        t = self._elapsed
        held: set[str] = set()
        if 2.5 <= t < 5.5:
            held.add("right")
        if 10.5 <= t < 12.0:
            held.add("down")
        pressed = {key for (trigger, key) in self._DEMO_EVENTS if self._demo_last_t <= trigger < t}
        self._demo_last_t = t
        self._demo_held = held
        self._demo_pressed = pressed
        if t >= 16.0:
            print("Demo complete - closing window.")
            self.close()

    # -- loop ------------------------------------------------------------

    def update(self, dt: float) -> None:
        self._elapsed += dt
        if self.demo:
            self._demo_step()

    def close(self) -> None:
        self.assets.clear()
        self._tmp.cleanup()
        super().close()


# -- headless checks -----------------------------------------------------


def run_checks():
    ok = 0
    tmp = tempfile.TemporaryDirectory()
    backend = NullBackend()
    player_path = os.path.join(tmp.name, "player.png")
    coin_path = os.path.join(tmp.name, "coin.png")
    with open(player_path, "wb") as handle:
        handle.write(_sheet_bytes(_player_frames()))
    with open(coin_path, "wb") as handle:
        handle.write(_png_bytes(CELL, CELL, _cell_rows(_coin_cell())))
    font_path = os.path.join(tmp.name, "fake.ttf")
    with open(font_path, "wb") as handle:
        handle.write(b"\x00\x01\x00\x00 fake ttf bytes")

    assets = pydex_ge.Assets(backend=backend)

    img1 = assets.image(coin_path)
    img2 = assets.image(coin_path)
    assert img1 is img2 and (img1.width, img1.height) == (CELL, CELL)
    ok += 1

    sheet1 = assets.sprite_sheet(player_path, CELL, CELL)
    sheet2 = assets.sprite_sheet(player_path, CELL, CELL)
    assert sheet1 is sheet2
    assert sheet1.image is assets.image(player_path)
    assert (sheet1.image.width, sheet1.image.height) == (CELL * 4, CELL)
    assert sheet1.cell(0, 0).width == CELL and sheet1.cell(3, 0).width == CELL
    ok += 1

    font1 = assets.font(font_path, 16)
    font2 = assets.font(font_path, 16)
    assert font1 is font2 and font1.size == 16
    ok += 1

    assert assets.contains(coin_path) and assets.contains(player_path)
    assert len(assets) == 4
    ok += 1

    removed = assets.remove(coin_path)
    assert removed == 1 and not assets.contains(coin_path)
    assert len(assets) == 3
    removed = assets.remove(player_path)
    assert removed == 2 and len(assets) == 1
    assert assets.remove(player_path) == 0
    ok += 1

    assets.clear()
    assets.clear()
    assert len(assets) == 0
    ok += 1

    class Obj:
        def __init__(self):
            self.updates = 0
            self.draws = 0
            self.events = 0

        def update(self, dt):
            self.updates += 1

        def draw(self, renderer):
            self.draws += 1

        def handle_event(self, event):
            self.events += 1

    scene = pydex_ge.Scene()
    obj = Obj()
    scene.add(obj)
    scene.update(0.1)
    scene.draw(None)
    scene.handle_event("q")
    assert (obj.updates, obj.draws, obj.events) == (1, 1, 1)
    assert len(scene) == 1 and obj in scene
    assert scene.remove(obj) is True and scene.remove(obj) is False
    scene.add(obj)
    scene.clear()
    assert len(scene) == 0
    ok += 1

    class TrackScene(pydex_ge.Scene):
        def __init__(self, name, log):
            super().__init__()
            self.name = name
            self.log = log

        def on_enter(self):
            self.log.append(f"{self.name}+")

        def on_exit(self):
            self.log.append(f"{self.name}-")

        def update(self, dt):
            self.log.append(f"{self.name}u")

    log = []
    a = TrackScene("a", log)
    b = TrackScene("b", log)
    c = TrackScene("c", log)
    manager = pydex_ge.SceneManager()
    manager.push(a)
    assert manager.current is a and log == ["a+"]
    manager.push(b)
    assert manager.current is b and len(manager) == 2
    assert log == ["a+", "b+"]
    manager.update(0.0)
    assert log == ["a+", "b+", "bu"]
    manager.pop()
    assert manager.current is a and len(manager) == 1
    assert log == ["a+", "b+", "bu", "b-"]
    manager.update(0.0)
    assert log == ["a+", "b+", "bu", "b-", "au"]
    ok += 1

    manager.replace(c)
    assert manager.current is c and len(manager) == 1
    assert log[-2:] == ["a-", "c+"]
    ok += 1

    try:
        manager.push(c)
        raise AssertionError("duplicate push should fail")
    except pydex_ge.ConfigurationError:
        ok += 1
    try:
        manager.push("not a scene")
        raise AssertionError("non-scene push should fail")
    except pydex_ge.ConfigurationError:
        ok += 1

    empty = pydex_ge.SceneManager()
    assert empty.pop() is None
    empty.replace(a)
    assert empty.current is a and len(empty) == 1
    empty.clear()
    assert len(empty) == 0 and empty.current is None
    ok += 1

    print(f"All {ok} Part 9 checks passed.")
    tmp.cleanup()


# -- entry point ---------------------------------------------------------


def main():
    if "--check" in sys.argv:
        run_checks()
        return
    ManualPart9Game(demo="--demo" in sys.argv).run()
    print("Game exited cleanly.")


if __name__ == "__main__":
    main()
