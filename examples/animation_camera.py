"""PYDEX Part 8 example: Animation + Camera + configurable frame rate.

A generated sprite-sheet character walks through a world larger than the
screen while a camera follows it.  UI labels stay fixed on screen while the
world moves underneath.

Controls
--------
* **Arrow keys** — move the player.
* **+ / -** — camera zoom (0.4x to 3.0x).
* **Space** — pause / resume the player animation.
* **R** — reset the player animation to frame 0.
* **F1 / F2 / F3 / F4** — 24 / 60 / 120 / unlimited FPS.
* **ESC** — quit (the example also closes itself after ~45 seconds).

Run with:  python examples/animation_camera.py
"""

from __future__ import annotations

import struct
import tempfile

import pydex_ge
from pydex_ge.physics import Rect

CELL = 32
WORLD_WIDTH = 2000
WORLD_HEIGHT = 1200


# -- tiny runtime sprite-sheet generator (standard library only) ---------


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


def _blank_cell() -> list[list[tuple[int, int, int, int]]]:
    return [[(0, 0, 0, 0)] * CELL for _ in range(CELL)]


def _stamp(cell, x: int, y: int, w: int, h: int, color) -> None:
    for row in range(y, y + h):
        for col in range(x, x + w):
            if 0 <= row < CELL and 0 <= col < CELL:
                cell[row][col] = color


def _character_cell(
    leg_left: tuple[int, int],
    leg_right: tuple[int, int],
    arms: list[tuple[int, int, int, int]],
) -> list[list[tuple[int, int, int, int]]]:
    """One 32x32 frame of a simple blocky character."""
    skin = (245, 210, 170, 255)
    hair = (70, 70, 95, 255)
    shirt = (80, 160, 255, 255)
    sleeve = (60, 130, 220, 255)
    pants = (45, 60, 90, 255)
    boot = (30, 30, 45, 255)
    eye = (20, 20, 20, 255)

    cell = _blank_cell()
    _stamp(cell, 13, 3, 6, 5, skin)
    _stamp(cell, 13, 2, 6, 2, hair)
    _stamp(cell, 15, 5, 1, 1, eye)
    _stamp(cell, 17, 5, 1, 1, eye)
    _stamp(cell, 12, 9, 8, 11, shirt)

    lx, ly = leg_left
    rx, ry = leg_right
    _stamp(cell, lx, ly, 3, 8, pants)
    _stamp(cell, rx, ry, 3, 8, pants)
    _stamp(cell, lx, ly + 8, 3, 3, boot)
    _stamp(cell, rx, ry + 8, 3, 3, boot)
    for ax, ay, aw, ah in arms:
        _stamp(cell, ax, ay, aw, ah, sleeve)
    return cell


def _sheet_rows() -> list[bytes]:
    frames = [
        _character_cell((13, 20), (16, 20), [(10, 10, 2, 7), (20, 10, 2, 7)]),
        _character_cell((12, 20), (17, 19), [(8, 9, 3, 7), (21, 10, 2, 7)]),
        _character_cell((13, 20), (16, 20), [(10, 10, 2, 7), (20, 10, 2, 7)]),
        _character_cell((17, 19), (12, 20), [(21, 9, 3, 7), (8, 10, 2, 7)]),
    ]
    rows: list[bytes] = []
    for row in range(CELL):
        line = bytearray()
        for frame in frames:
            for col in range(CELL):
                line += bytes(frame[row][col])
        rows.append(bytes(line))
    return rows


def _solid_pixels(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    row = bytes((*color, 255)) * width
    return row * height


class AnimationCameraGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Animation + Camera", 800, 600, fps=60)
        self.background = (22, 24, 34)

        self._tmp = tempfile.TemporaryDirectory()
        sheet_path = f"{self._tmp.name}/player_sheet.png"
        with open(sheet_path, "wb") as handle:
            handle.write(_png_bytes(CELL * 4, CELL, _sheet_rows()))
        sheet = pydex_ge.SpriteSheet(pydex_ge.Image(sheet_path), CELL, CELL)

        self.idle = pydex_ge.Animation([sheet.cell(0, 0)], fps=2, loop=True)
        self.walk = pydex_ge.Animation(
            [sheet.cell(0, 0), sheet.cell(1, 0), sheet.cell(2, 0), sheet.cell(3, 0)],
            fps=10,
            loop=True,
        )

        self.player = pydex_ge.Sprite(sheet.image)
        self.player.position = (400, 1000)
        self.player.animations["idle"] = self.idle
        self.player.animations["walk"] = self.walk
        self.player.play_animation("idle")

        self.floor = pydex_ge.Sprite.from_pixels(WORLD_WIDTH, 40, _solid_pixels(WORLD_WIDTH, 40, (70, 90, 120)))
        self.floor.position = (0, WORLD_HEIGHT - 40)
        self.platforms = []
        for x, y in ((500, 880), (1100, 720), (1500, 600)):
            platform = pydex_ge.Sprite.from_pixels(200, 24, _solid_pixels(200, 24, (120, 140, 175)))
            platform.position = (x, y)
            self.platforms.append(platform)

        self.camera = pydex_ge.Camera(800, 600, position=(400, 1000))
        self.camera.bounds = Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)
        self.camera.follow(self.player, smoothing=4.0)

        font = pydex_ge.Font(size=16)
        small = pydex_ge.Font(size=13)
        self.hint = pydex_ge.Label(
            "Arrows: move    +/-: zoom    Space: pause/resume    R: reset    "
            "F1-24  F2-60  F3-120  F4-unlimited    ESC: quit",
            font=small,
            position=(20, 20),
            color=(150, 160, 185),
        )
        self.status = pydex_ge.Label(
            "FPS: 60    anim: idle    frame: 0/1    cam (0,0) zoom 1.00",
            font=font,
            position=(20, 44),
            color=(120, 255, 120),
        )
        self.screen_pos = pydex_ge.Label(
            "player screen (0,0)",
            font=small,
            position=(20, 68),
            color=(255, 220, 120),
        )

        self.elapsed = 0.0
        self.animation_paused = False
        self.move_speed = 260.0

    # -- helpers ----------------------------------------------------------

    @property
    def fps_label(self) -> str:
        if self.fps is None:
            return "Unlimited"
        return f"{int(self.fps)} FPS"

    def _current_anim_name(self) -> str:
        for name, animation in self.player.animations.items():
            if self.player.animation is animation:
                return name
        return "none"

    # -- loop -------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.elapsed += dt

        moving = False
        if self.input.is_key_down("left"):
            self.player.x -= int(self.move_speed * dt)
            moving = True
        if self.player.x < 0:
            self.player.x = 0
        if self.input.is_key_down("right"):
            self.player.x += int(self.move_speed * dt)
            moving = True
        if self.player.x > WORLD_WIDTH - CELL:
            self.player.x = WORLD_WIDTH - CELL
        if self.input.is_key_down("up"):
            self.player.y -= int(self.move_speed * dt)
            moving = True
        if self.player.y < 0:
            self.player.y = 0
        if self.input.is_key_down("down"):
            self.player.y += int(self.move_speed * dt)
            moving = True
        if self.player.y > WORLD_HEIGHT - CELL:
            self.player.y = WORLD_HEIGHT - CELL

        if moving:
            self.player.play_animation("walk")
        else:
            self.player.play_animation("idle")

        if self.input.is_key_pressed("space"):
            self.animation_paused = not self.animation_paused
            if self.animation_paused:
                self.player.animation.pause()
            else:
                self.player.animation.resume()
        if self.input.is_key_pressed("r"):
            self.player.animation.reset()

        if self.input.is_key_pressed("minus"):
            self.camera.zoom = round(max(0.4, self.camera.zoom * 0.9), 2)
        if self.input.is_key_pressed("equals"):
            self.camera.zoom = round(min(3.0, self.camera.zoom * 1.1), 2)

        if self.input.is_key_pressed("f1"):
            self.fps = 24
        if self.input.is_key_pressed("f2"):
            self.fps = 60
        if self.input.is_key_pressed("f3"):
            self.fps = 120
        if self.input.is_key_pressed("f4"):
            self.fps = None

        self.player.update(dt)
        self.camera.update(dt)

        animation = self.player.animation
        self.status.text = (
            f"FPS: {self.fps_label}    anim: {self._current_anim_name()}    "
            f"frame: {animation.frame_index + 1}/{animation.frame_count}    "
            f"cam ({int(self.camera.position.x)},{int(self.camera.position.y)}) "
            f"zoom {self.camera.zoom:.2f}"
        )
        screen = self.camera.world_to_screen(self.player.position)
        self.screen_pos.text = (
            f"player world ({self.player.x},{self.player.y}) -> "
            f"screen ({int(screen.x)},{int(screen.y)})"
        )

        if self.input.is_key_pressed("escape") or self.elapsed > 45.0:
            self.close()

    def draw(self) -> None:
        self.camera.begin(self.renderer)
        self.renderer.draw_sprite(self.floor)
        for platform in self.platforms:
            self.renderer.draw_sprite(platform)
        self.player.draw(self.renderer)
        self.camera.end()

        self.renderer.draw_label(self.hint)
        self.renderer.draw_label(self.status)
        self.renderer.draw_label(self.screen_pos)


def main() -> None:
    game = AnimationCameraGame()
    print(
        "PYDEX animation + camera example.\n"
        "Move with the arrow keys, zoom with +/-, pause/resume with Space, "
        "reset with R, change FPS with F1-F4, quit with ESC."
    )
    game.run()
    print("AnimationCameraGame closed cleanly.")


if __name__ == "__main__":
    main()
