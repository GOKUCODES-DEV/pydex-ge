"""Temporary manual test for Part 12: Advanced 2D.

Exercises every Part 12 feature in one windowed demo:

* :class:`pydex_ge.Transform2D` parents/children and world transforms,
* sprite transforms (``rotation``, ``origin``, ``flip_x``/``flip_y``,
  per-axis ``scale``, ``parent``, ``z``),
* renderer + backend transform forwarding (angle/center/flip/color-mod),
* scene z-order (stable, ``z`` attribute),
* :class:`pydex_ge.Parallax` layers,
* camera ``dead_zone`` and deterministic ``shake()``,
* :class:`pydex_ge.TileMap` with camera-culled rendering and tile collision,
* animation states (``add_animation``/``play_animation``/``on_finish``/
  ``stop_animation``),
* 2D effects (``fade_to``, ``flash``, ``tint``),
* scene integration and the public exports.

Run modes::

    python examples/manual_advanced_2d_test.py --check   # headless math checks, no window
    python examples/manual_advanced_2d_test.py --demo    # auto-driven windowed run
    python examples/manual_advanced_2d_test.py           # interactive windowed run

Controls: arrows move, SPACE jump, 1/2 force idle/walk animation,
T toggle a tile platform, Z shake, +/- zoom, F follow, G smoothing,
D dead zone, ESC quit.

This file is a manual verification aid only; it is not part of the public
PYDEX API and may be deleted at any time.
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile
import zlib

import pydex_ge
from pydex_ge.physics import Rect, Vector2

SCREEN_W, SCREEN_H = 800, 600
WORLD = Rect(0, 0, 40 * 32, 24 * 32)  # 1280 x 768

PALETTE = {
    ".": (0, 0, 0, 0),
    "H": (70, 50, 40, 255),
    "F": (240, 210, 180, 255),
    "S": (60, 130, 220, 255),
    "P": (50, 80, 150, 255),
    "B": (40, 40, 55, 255),
}

IDLE_FRAME = [
    "................",
    "......HH........",
    ".....FFFF.......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....SSSSSS......",
    ".....PP.........",
    ".....PP.........",
    ".....PP.........",
    ".....PP.........",
    ".....PP.........",
    "....BBBB........",
    "....BBBB........",
    "................",
    "................",
]

WALK_A = [
    "................",
    "......HH........",
    ".....FFFF.......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....P...P.......",
    "....P...P.......",
    "....P...P.......",
    "....P...P.......",
    "....B...B.......",
    "...BB...BB......",
    "................",
    "................",
    "................",
]

WALK_B = [
    "................",
    "......HH........",
    ".....FFFF.......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....SSSSSS......",
    ".....PP.........",
    ".....PP.........",
    ".....PP.........",
    "....P..P........",
    "....P..P........",
    "...BB..BB.......",
    "................",
    "................",
    "................",
]

JUMP_FRAME = [
    "................",
    "......HH........",
    ".....FFFF.......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....SSSSSS......",
    "....SSSSSS......",
    ".....PP.........",
    "....P..P........",
    "....P..P........",
    "....P..P........",
    "...BB..BB.......",
    "................",
    "................",
    "................",
    "................",
]


def _rgba_bytes(r, g, b, a, count):
    return bytes((r, g, b, a)) * count


def _frame_sprite(rows, palette=PALETTE):
    data = bytearray()
    for row in rows:
        if len(row) != 16:
            raise ValueError("pixel-art rows must be 16 chars wide")
        for char in row:
            data += bytes(palette[char])
    return pydex_ge.Sprite.from_pixels(16, 16, bytes(data))


def _circle_pixels(diameter, color=(255, 255, 255), alpha=255):
    center = diameter / 2
    radius = center - 1
    data = bytearray()
    for y in range(diameter):
        for x in range(diameter):
            dx, dy = x - center, y - center
            if dx * dx + dy * dy <= radius * radius:
                data += bytes(color + (alpha,))
            else:
                data += b"\x00\x00\x00\x00"
    return bytes(data)


def _silhouette_pixels(width, height, color):
    data = bytearray()
    for y in range(height):
        for x in range(width):
            t = abs(x - width / 2) / (width / 2)
            ridge = height - int(t * height * 0.75) - int(height * 0.08)
            if y >= ridge:
                data += bytes(color + (255,))
            else:
                data += b"\x00\x00\x00\x00"
    return bytes(data)


def _png_bytes(width, height, raw):
    def chunk(tag, payload):
        body = tag + payload
        return (
            struct.pack(">I", len(payload))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _tile_sheet_bytes():
    width, height = 64, 32
    raw = bytearray()
    for y in range(height):
        raw += b"\x00"
        for x in range(width):
            if x // 32 == 0:
                color = (70, 140, 90)  # grass
            else:
                color = (130, 100, 80)  # stone
            raw += bytes(color + (255,))
    return _png_bytes(width, height, bytes(raw))


class Player:
    z = 5

    def __init__(self, tilemap, spawn=(96, 96)):
        self.body = pydex_ge.Body(position=spawn, size=(16, 26))
        self.tilemap = tilemap
        self.held = set()
        self.jump_pressed = False
        self.on_ground = False
        self.face = 1
        self.sprite = _frame_sprite(IDLE_FRAME)
        self.sprite.add_animation(
            "idle", pydex_ge.Animation([_frame_sprite(IDLE_FRAME)], fps=4, loop=True)
        )
        self.sprite.add_animation(
            "walk",
            pydex_ge.Animation(
                [_frame_sprite(WALK_A), _frame_sprite(WALK_B)], fps=8, loop=True
            ),
        )
        self.sprite.add_animation(
            "jump",
            pydex_ge.Animation([_frame_sprite(JUMP_FRAME)], fps=8, loop=False),
        )
        self.sprite.play_animation("idle")

    @property
    def animation(self):
        return self.sprite.current_animation

    def jump(self):
        if not self.on_ground:
            return
        self.body.velocity = (self.body.velocity.x, -320)
        self.on_ground = False
        self.sprite.play_animation(
            "jump", on_finish=lambda: self.sprite.play_animation("idle")
        )

    def update(self, dt):
        vx = 0.0
        if pydex_ge.Keys.LEFT in self.held:
            vx = -180.0
        if pydex_ge.Keys.RIGHT in self.held:
            vx = 180.0
        self.body.velocity = (vx, self.body.velocity.y + 600 * dt)
        if self.jump_pressed:
            self.jump()
        self.jump_pressed = False

        was_falling = self.body.velocity.y > 0
        self.body.update(dt)
        collided = self.tilemap.collide_body(self.body)
        if was_falling and collided and abs(self.body.velocity.y) < 1e-9:
            self.sprite.flash(0.3)
        self.on_ground = abs(self.body.velocity.y) < 1e-9 and collided

        if self.body.position.x < 0:
            self.body.position = (0, self.body.position.y)
        if self.body.position.x > WORLD.right - 16:
            self.body.position = (WORLD.right - 16, self.body.position.y)

        if vx != 0:
            self.face = 1 if vx > 0 else -1
            if self.on_ground and self.animation != "walk":
                self.sprite.play_animation("walk")
        elif self.on_ground and self.animation not in ("idle", "jump"):
            self.sprite.play_animation("idle")

        self.sprite.flip_x = self.face < 0
        self.sprite.x = round(self.body.position.x)
        self.sprite.y = round(self.body.position.y)
        self.sprite.update(dt)

    def draw(self, renderer):
        renderer.draw_sprite(self.sprite)


class Orb:
    z = 10

    def __init__(self, player):
        self.player = player
        self.pivot = pydex_ge.Transform2D(position=(0, 0), rotation=0)
        self.sprite = pydex_ge.Sprite.from_pixels(24, 24, _circle_pixels(24))
        self.sprite.parent = self.pivot
        self.sprite.origin = (0.5, 0.5)
        self.angle = 0.0
        self._tints = ((255, 80, 80), (80, 255, 80), (80, 80, 255))

    def update(self, dt):
        self.pivot.position = (
            self.player.body.position.x + 34,
            self.player.body.position.y + 12,
        )
        self.pivot.rotation += 60 * dt
        self.angle = (self.angle + 120 * dt) % 360
        self.sprite.rotation = self.angle
        self.sprite.flip_x = int(self.angle // 45) % 2 == 1
        self.sprite.tint = self._tints[int(self.angle // 120) % 3]
        self.sprite.update(dt)

    def draw(self, renderer):
        renderer.draw_sprite(self.sprite)


class Ghost:
    z = -3

    def __init__(self, position=(360, 180)):
        self.sprite = pydex_ge.Sprite.from_pixels(20, 20, _circle_pixels(20, (180, 190, 255), 200))
        self.sprite.position = position
        self.sprite.alpha = 20
        self.fading_up = False
        self.sprite.fade_to(255, 2.0)
        self.fading_up = True

    def update(self, dt):
        self.sprite.update(dt)
        if self.fading_up and self.sprite.alpha >= 245:
            self.fading_up = False
            self.sprite.fade_to(20, 2.0)
        elif not self.fading_up and self.sprite.alpha <= 25:
            self.fading_up = True
            self.sprite.fade_to(255, 2.0)

    def draw(self, renderer):
        renderer.draw_sprite(self.sprite)


class Advanced2DGame(pydex_ge.Game):
    def __init__(self, demo=False):
        super().__init__("PYDEX Part 12 manual test", SCREEN_W, SCREEN_H, fps=60)
        self.demo = demo
        self._elapsed = 0.0
        self._held = set()
        self._jump = False

        self.tileset_path = os.path.join(tempfile.gettempdir(), "pydex_part12_sheet.png")
        with open(self.tileset_path, "wb") as handle:
            handle.write(_tile_sheet_bytes())

        self.tilemap = pydex_ge.TileMap(40, 24, tile_size=(32, 32))
        self.tilemap.sprite_sheet = pydex_ge.SpriteSheet(pydex_ge.Image(self.tileset_path), 32, 32)
        self.tilemap.set_solid(1)
        self.tilemap.set_solid(2)
        self._build_level()
        self._platform_rows = [(14, 20, 14, 15), (28, 34, 10, 11)]

        self.player = Player(self.tilemap, spawn=(96, 96))
        self.orb = Orb(self.player)
        self.ghost = Ghost()
        self.sky = pydex_ge.Sprite.from_pixels(1, 1, _rgba_bytes(40, 50, 90, 255, 1))
        self.sky.scale = (WORLD.right + 320, WORLD.bottom + 320)
        self.mountains = pydex_ge.Sprite.from_pixels(400, 120, _silhouette_pixels(400, 120, (70, 90, 110)))
        self.mountains.position = (0, 640)
        self.mountains.scale = (2.0, 2.0)
        self.hills = pydex_ge.Sprite.from_pixels(400, 80, _silhouette_pixels(400, 80, (90, 110, 90)))
        self.hills.position = (200, 680)
        self.hills.scale = (2.5, 2.5)

        self.parallax = [
            pydex_ge.Parallax(self.sky, factor=0.05),
            pydex_ge.Parallax(self.mountains, factor=0.3),
            pydex_ge.Parallax(self.hills, factor=0.55),
        ]
        self.parallax[0].z = -100
        self.parallax[1].z = -50
        self.parallax[2].z = -20
        self.tilemap.z = 0

        self.camera = pydex_ge.Camera2D(SCREEN_W, SCREEN_H, position=(400, 300))
        self.camera.bounds = WORLD
        self.camera.follow(self.player.body.position, smoothing=3.0)
        self.camera.dead_zone = (120, 100)
        self.follow_on = True
        self.smoothing_on = True
        self.dead_zone_on = True

        self.scene = pydex_ge.Scene(camera=self.camera)
        for layer in self.parallax:
            self.scene.add(layer)
        self.scene.add(self.ghost)
        self.scene.add(self.tilemap)
        self.scene.add(self.player)
        self.scene.add(self.orb)

        self._font = pydex_ge.Font(size=14)
        self._labels = [
            pydex_ge.Label("", font=self._font, position=(12, 10 + i * 18), color=(240, 240, 240))
            for i in range(6)
        ]

        print("PYDEX Part 12 manual test.")
        print(
            "Controls: arrows move, SPACE jump, 1/2 force idle/walk, T platform, "
            "Z shake, +/- zoom, F follow, G smoothing, D dead zone, ESC quit."
        )
        print("Demo mode on." if demo else "Interactive mode.")

    def _build_level(self):
        t = self.tilemap
        for col in range(40):
            for row in range(21, 24):
                t.set_tile(col, row, 1)
        for row in range(14, 21):
            for col in (8, 9, 30, 31):
                t.set_tile(col, row, 2)
        for col in range(14, 21):
            t.set_tile(col, 14, 1)
            t.set_tile(col, 15, 1)
        for col in range(28, 35):
            t.set_tile(col, 10, 1)
            t.set_tile(col, 11, 1)

    def _toggle_platform(self):
        rows = self._platform_rows.pop(0)
        self._platform_rows.append(rows)
        col_start, col_end, row_a, row_b = rows
        for col in range(col_start, col_end + 1):
            self.tilemap.set_tile(col, row_a, 0)
            self.tilemap.set_tile(col, row_b, 0)

    def _demo_step(self):
        t = self._elapsed
        if t < 4:
            self._held = {pydex_ge.Keys.RIGHT}
        elif t < 7:
            self._held = {pydex_ge.Keys.LEFT}
        elif t < 10:
            self._held = {pydex_ge.Keys.RIGHT, pydex_ge.Keys.UP}
        else:
            self._held = set()
        if int(t) % 3 == 0 and int(t - 0.1) % 3 != 0:
            self._jump = True
        if 11 <= t < 11.5:
            self.camera.shake(8, 0.5)
        if 12 <= t < 13:
            self.camera.zoom = 1.0 + (t - 12.0) * 0.8
        if t >= 15:
            print("Demo complete - closing window.")
            self.close()

    def _read_input(self):
        held = set()
        for name in (pydex_ge.Keys.LEFT, pydex_ge.Keys.RIGHT, pydex_ge.Keys.UP, pydex_ge.Keys.DOWN):
            if self.input.is_key_down(name):
                held.add(name)
        if self.input.is_key_pressed(pydex_ge.Keys.SPACE):
            self._jump = True
        if self.input.is_key_pressed(pydex_ge.Keys.ONE):
            self.player.sprite.play_animation("idle")
        if self.input.is_key_pressed(pydex_ge.Keys.TWO):
            self.player.sprite.play_animation("walk")
        if self.input.is_key_pressed(pydex_ge.Keys.T):
            self._toggle_platform()
        if self.input.is_key_pressed(pydex_ge.Keys.Z):
            self.camera.shake(10, 0.4)
        if self.input.is_key_pressed(pydex_ge.Keys.EQUALS):
            self.camera.zoom = min(2.5, self.camera.zoom * 1.25)
        if self.input.is_key_pressed(pydex_ge.Keys.MINUS):
            self.camera.zoom = max(0.5, self.camera.zoom / 1.25)
        if self.input.is_key_pressed(pydex_ge.Keys.F):
            self.follow_on = not self.follow_on
            self._apply_follow()
        if self.input.is_key_pressed(pydex_ge.Keys.G):
            self.smoothing_on = not self.smoothing_on
            self._apply_follow()
        if self.input.is_key_pressed(pydex_ge.Keys.D):
            self.dead_zone_on = not self.dead_zone_on
            self.camera.dead_zone = (120, 100) if self.dead_zone_on else None
        if self.input.is_key_pressed(pydex_ge.Keys.ESCAPE):
            self.close()

    def _apply_follow(self):
        if self.follow_on:
            self.camera.follow(self.player.body.position, smoothing=3.0 if self.smoothing_on else 0.0)
        else:
            self.camera.clear_follow()

    def update(self, dt):
        self._elapsed += dt
        if self.demo:
            self._demo_step()
        else:
            self._read_input()
        self.player.held = self._held
        self.player.jump_pressed = self._jump
        self._jump = False

        self.scene.update(dt)
        self.camera.update(dt)

    def draw(self):
        r = self.renderer
        r.clear((18, 18, 24))
        self.scene.draw(r)

        shake_x, shake_y = self.camera.shake_offset
        self._labels[0].text = (
            f"PLAYER ({self.player.body.position.x:.0f}, {self.player.body.position.y:.0f})  "
            f"anim {self.player.animation}  ground {self.player.on_ground}"
        )
        self._labels[1].text = (
            f"CAM ({self.camera.x:.0f}, {self.camera.y:.0f}) zoom {self.camera.zoom:.2f}  "
            f"follow {self.follow_on} smooth {self.smoothing_on} deadzone {self.dead_zone_on}"
        )
        self._labels[2].text = (
            f"SHAKE offset ({shake_x:.1f}, {shake_y:.1f}) active {self.camera.shaking}  "
            f"orb rot {self.orb.sprite.rotation:.0f} flip {self.orb.sprite.flip_x}"
        )
        self._labels[3].text = (
            f"ORB tint {self.orb.sprite.tint}  pivot world "
            f"({self.orb.pivot.world_position.x:.0f}, {self.orb.pivot.world_position.y:.0f})"
        )
        self._labels[4].text = f"GHOST alpha {self.ghost.sprite.alpha}  tiles z={self.tilemap.z} player z={self.player.z}"
        self._labels[5].text = "arrows move | SPACE jump | 1/2 anim | T platform | Z shake | +/- zoom | F/G/D toggles | ESC quit"
        for label in self._labels:
            r.draw_label(label)


def run_checks():
    ok = 0

    # 1. Transform2D
    ship = pydex_ge.Transform2D(position=(100, 50), rotation=45, scale=2)
    gun = pydex_ge.Transform2D(position=(20, 0), parent=ship)
    assert gun.world_position == Vector2(120, 50)
    ship.position = (200, 80)
    assert gun.world_position == Vector2(220, 80)
    assert ship.world_rotation == 45.0
    child = pydex_ge.Transform2D(rotation=10, scale=2, parent=ship)
    assert child.world_rotation == 55.0
    assert child.world_scale == 4.0
    assert pydex_ge.Transform2D(position=(1, 2)) == pydex_ge.Transform2D(position=(1, 2))
    ok += 1

    # 2. Sprite transforms
    sprite = pydex_ge.Sprite.from_pixels(16, 16, _rgba_bytes(255, 255, 255, 255, 256))
    sprite.rotation = 90
    sprite.origin = (0.5, 0.5)
    sprite.flip_x = True
    sprite.flip_y = False
    sprite.scale = (2, 1)
    assert sprite.rotation == 90.0
    assert sprite.origin == (0.5, 0.5)
    assert sprite.flip_x and not sprite.flip_y
    assert sprite.scale == (2.0, 1.0)
    parent = pydex_ge.Transform2D(position=(10, 20))
    sprite.parent = parent
    sprite.position = (5, 5)
    assert sprite.world_position == Vector2(15, 25)
    ok += 1

    # 3. Renderer + backend transform forwarding
    from pydex_ge.backend.null import NullRenderer

    renderer = pydex_ge.Renderer(NullRenderer())
    sprite = pydex_ge.Sprite.from_pixels(16, 16, _rgba_bytes(255, 255, 255, 255, 256))
    sprite.rotation = 45
    sprite.origin = (1.0, 0.5)
    sprite.tint = (255, 0, 0)
    sprite.draw(renderer)
    draws = renderer._renderer.transformed_draws
    assert len(draws) == 1
    _, src, dst, alpha, angle, center, flip, color_mod = draws[0]
    assert angle == 45.0
    assert center == (16, 8)
    assert color_mod == (255, 0, 0)
    assert dst == (-16, -8, 16, 16)
    ok += 1

    # 4. Scene stable z-order
    scene = pydex_ge.Scene()
    order = []

    class _Track:
        def __init__(self, name, z=0):
            self.name = name
            self.z = z

        def draw(self, renderer):
            order.append(self.name)

    scene.add(_Track("front", 5))
    scene.add(_Track("mid", 0))
    scene.add(_Track("back", -5))
    scene.add(_Track("plain"))  # z defaults to 0
    scene.draw(renderer)
    assert order == ["back", "mid", "plain", "front"], order
    ok += 1

    # 5. Parallax math + draw restore
    parallax = pydex_ge.Parallax(sprite, factor=0.5)
    camera = pydex_ge.Camera(position=(100, 50))
    assert parallax.offset(camera) == (50.0, 25.0)
    sprite.position = (7, 9)
    renderer.begin_camera(camera)
    try:
        parallax.draw(renderer)
    finally:
        renderer.end_camera()
    assert sprite.position == (7, 9)
    ok += 1

    # 6. Camera dead zone
    cam = pydex_ge.Camera(position=(0, 0))
    cam.dead_zone = (100, 100)
    target = Vector2(40, 0)
    cam.follow(target, smoothing=0)
    cam.update(0.016)
    assert cam.position == Vector2(0, 0)
    target.x = 60  # move the followed object itself
    cam.update(0.016)
    assert cam.position == Vector2(10, 0)
    ok += 1

    # 7. Camera shake: deterministic, decays, ends exactly at (0, 0)
    first = pydex_ge.Camera()
    second = pydex_ge.Camera()
    first.shake(8, 1.0)
    second.shake(8, 1.0)
    for _ in range(5):
        first.update(0.1)
        second.update(0.1)
    assert first.shake_offset == second.shake_offset
    first.update(0.6)
    assert first.shake_offset == (0.0, 0.0)
    assert not first.shaking
    ok += 1

    # 8. TileMap grid, solid runs, culled render
    from pydex_ge.backend.null import NullBackend

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "sheet.png")
    with open(path, "wb") as handle:
        handle.write(_tile_sheet_bytes())
    image = pydex_ge.Image(path, backend=NullBackend())
    sheet = pydex_ge.SpriteSheet(image, 32, 32)
    tiles = pydex_ge.TileMap(4, 3, tile_size=(32, 32), sprite_sheet=sheet)
    tiles.set_tile(0, 0, 1)
    tiles.set_tile(1, 0, 1)
    tiles.set_tile(2, 0, 1)
    tiles.set_solid(1)
    rects = tiles.solid_rects()
    assert len(rects) == 1 and rects[0].width == 96 and rects[0].height == 32
    assert tiles.tile_at(70, 10) == (2, 0)
    ok += 1

    # 9. Tile collision
    body = pydex_ge.Body(position=(40, 20), size=(16, 16), velocity=(0, 100))
    assert tiles.collide_body(body)
    assert body.position == Vector2(40, 32)  # pushed out below the solid run
    assert body.velocity == Vector2(0, 0)
    ok += 1

    # 10. Animation states + on_finish
    anim_sprite = pydex_ge.Sprite.from_pixels(4, 4, _rgba_bytes(255, 255, 255, 255, 16))
    frames = [
        pydex_ge.Sprite.from_pixels(4, 4, _rgba_bytes(255, 0, 0, 255, 16)),
        pydex_ge.Sprite.from_pixels(4, 4, _rgba_bytes(0, 255, 0, 255, 16)),
    ]
    anim_sprite.add_animation("boom", pydex_ge.Animation(frames, fps=10, loop=False))
    calls = []
    anim_sprite.play_animation("boom", on_finish=lambda: calls.append("done"))
    anim_sprite.update(0.5)
    assert calls == ["done"]
    anim_sprite.stop_animation()
    assert anim_sprite.current_animation is None
    ok += 1

    # 11. Effects: Fade, Flash, Tint + sprite helpers
    from pydex_ge.graphics.effects import Fade, Flash, Tint

    fade = Fade(0, 255, 1.0)
    fade.update(0.5)
    assert fade.alpha == 128
    flash = Flash(1.0)
    flash.update(0.5)
    assert abs(flash.strength - 0.5) < 1e-9
    assert Tint((1, 2, 3)) == Tint((1, 2, 3))
    effect_sprite = pydex_ge.Sprite.from_pixels(4, 4, _rgba_bytes(255, 255, 255, 255, 16))
    effect_sprite.fade_to(0, 1.0)
    effect_sprite.update(1.0)
    assert effect_sprite.alpha == 0
    effect_sprite.flash(1.0)
    effect_sprite.update(0.25)
    assert abs(effect_sprite.flash_strength - 0.75) < 1e-9
    ok += 1

    # 12. Public exports
    for name in ("Transform2D", "TileMap", "Parallax"):
        assert hasattr(pydex_ge, name), name
    from pydex_ge.graphics import Fade as GFade
    from pydex_ge.graphics import Flash as GFlash
    from pydex_ge.graphics import Parallax as GParallax
    from pydex_ge.graphics import Tint as GTint

    assert GFade is Fade and GFlash is Flash and GTint is Tint
    assert GParallax is parallax.__class__
    ok += 1

    # 13. Coordinate roundtrip with shake (visual-only correctness)
    cam = pydex_ge.Camera(position=(300, 200))
    cam.shake(6, 1.0)
    cam.update(0.2)
    dx, dy = cam.shake_offset
    screen = cam.world_to_screen((300, 200))
    assert abs(screen.x - (400 + dx)) < 1e-6
    assert abs(screen.y - (300 + dy)) < 1e-6
    back = cam.screen_to_world(screen)
    assert abs(back.x - 300) < 1e-6 and abs(back.y - 200) < 1e-6
    ok += 1

    print(f"All {ok} Advanced 2D checks passed.")


def main():
    if "--check" in sys.argv:
        run_checks()
        return
    Advanced2DGame(demo="--demo" in sys.argv).run()
    print("Game exited cleanly.")


if __name__ == "__main__":
    main()
