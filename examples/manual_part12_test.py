"""Temporary interactive manual test for Part 12: Advanced 2D (integrated).

A small playable scene that exercises the complete advanced 2D system at
once, the way a real game would use it, so you can verify the pieces work
together rather than in isolation:

* input / keyboard, physics + gravity, :class:`pydex_ge.TileMap` rendering
  with tile collision,
* sprite animation + animation states (``idle``/``walk``/``jump``/``twirl``),
* :class:`pydex_ge.Transform2D` parent/child hierarchy with rotation, scale,
  origin, and world transforms (the orbiting orb),
* camera follow / smoothing / dead zone / zoom / shake,
* :class:`pydex_ge.Parallax` layers,
* sprite effects (``fade_to``, ``flash``, ``tint``),
* :class:`pydex_ge.SceneManager` transitions (push/replace/pop via ``P`` and
  the auto-popping overlay scene),
* asset loading + caching via :class:`pydex_ge.Assets` (the tile sheet),
* scene z-order.

Run modes::

    python examples/manual_part12_test.py --check   # headless checks, no window
    python examples/manual_part12_test.py --demo    # auto-driven windowed run
    python examples/manual_part12_test.py           # interactive windowed run

Controls::

    arrows  move            R   spin test (rotation + twirl animation)
    SPACE   jump            + / -  camera zoom
    G       camera mode     F   toggle follow
    C       camera shake    T   cycle orb tint + player flash
    P       push/pop overlay scene
    ESC     quit

HUD shows player position/velocity, animation state, on-ground, camera
position/zoom/mode, scene + stack depth, asset cache status, and a live
PASS/FAIL sanity check.  This file is a manual verification aid only; it
is not part of the public PYDEX API and may be deleted at any time.
"""

from __future__ import annotations

import math
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

TWIRL_FRAME = [
    "................",
    ".....HH.........",
    "....FFFF........",
    "...S....S.......",
    "...S....S.......",
    "....SSSS........",
    "....SSSS........",
    ".....PP.........",
    "....P.P.........",
    "...P...P........",
    "...P...P........",
    "...BB.BB........",
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
        self.spinning = False
        self.landed_flash = 0.0
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
        self.sprite.add_animation(
            "twirl",
            pydex_ge.Animation([_frame_sprite(TWIRL_FRAME)], fps=10, loop=True),
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

        if self.spinning:
            self.sprite.rotation = (self.sprite.rotation + 720 * dt) % 360
            if self.animation != "twirl":
                self.sprite.play_animation("twirl")
        else:
            self.sprite.rotation = 0.0
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


class PlayerMarker:
    """A red crosshair at the physics body's position.

    Drawn in world space so that even if the sprite's transforms break,
    you can see exactly where the physics engine thinks the player is.
    """

    z = 50

    def __init__(self, player):
        self.player = player

    def draw(self, renderer):
        x, y = round(self.player.body.position.x), round(self.player.body.position.y)
        r = renderer.draw
        r.line(x - 8, y, x + 8, y, color=(255, 40, 40))
        r.line(x, y - 8, x, y + 8, color=(255, 40, 40))
        r.line(x - 5, y - 5, x + 5, y + 5, color=(255, 40, 40))
        r.line(x - 5, y + 5, x + 5, y - 5, color=(255, 40, 40))


class Orb:
    z = 10

    def __init__(self, player):
        self.player = player
        self.pivot = pydex_ge.Transform2D(position=(0, 0), rotation=0)
        self.ring = pydex_ge.Transform2D(position=(0, 30), parent=self.pivot)
        self.sprite = pydex_ge.Sprite.from_pixels(24, 24, _circle_pixels(24))
        self.sprite.parent = self.pivot
        self.sprite.origin = (0.5, 0.5)
        self.ring_sprite = pydex_ge.Sprite.from_pixels(14, 14, _circle_pixels(14, (255, 220, 120), 220))
        self.ring_sprite.parent = self.ring
        self.ring_sprite.origin = (0.5, 0.5)
        self.ring_sprite.z = 11
        self.angle = 0.0
        self._tints = ((255, 80, 80), (80, 255, 80), (80, 80, 255), (255, 255, 255))
        self.tint_index = 0
        self.sprite.tint = self._tints[0]

    def cycle_tint(self):
        self.tint_index = (self.tint_index + 1) % len(self._tints)
        self.sprite.tint = self._tints[self.tint_index]

    def update(self, dt):
        self.pivot.position = (
            self.player.body.position.x + 34,
            self.player.body.position.y + 12,
        )
        self.pivot.rotation += 60 * dt
        self.ring.rotation += 220 * dt
        self.angle = (self.angle + 120 * dt) % 360
        self.sprite.rotation = self.angle
        self.sprite.flip_x = int(self.angle // 45) % 2 == 1
        self.ring_sprite.flip_y = int(self.angle // 90) % 2 == 1
        self.sprite.update(dt)
        self.ring_sprite.update(dt)

    def draw(self, renderer):
        renderer.draw_sprite(self.ring_sprite)
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


class PlayScene(pydex_ge.Scene):
    CAMERA_MODES = ("smooth+dead", "smooth", "dead", "raw")

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.cam_mode = 0
        self.follow_on = True
        self.overlay = None

        self.player = Player(game.tilemap, spawn=(96, 96))
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
        game.tilemap.z = 0

        self.camera = pydex_ge.Camera2D(SCREEN_W, SCREEN_H, position=(400, 300))
        self.camera.bounds = WORLD
        self.camera.follow(self.player.body.position, smoothing=3.0)
        self.camera.dead_zone = (120, 100)

        for layer in self.parallax:
            self.add(layer)
        self.add(self.ghost)
        self.add(game.tilemap)
        self.add(self.player)
        self.add(PlayerMarker(self.player))
        self.add(self.orb)

        self._font = pydex_ge.Font(size=14)
        self._labels = [
            pydex_ge.Label("", font=self._font, position=(12, 10 + i * 18), color=(240, 240, 240))
            for i in range(7)
        ]

    # -- SceneManager lifecycle -----------------------------------------

    def on_enter(self):
        print("PlayScene entered")
        super().on_enter()

    def on_exit(self):
        print("PlayScene exited")
        super().on_exit()

    # -- helpers ---------------------------------------------------------

    def _apply_follow(self):
        if self.follow_on:
            self.camera.follow(
                self.player.body.position,
                smoothing=3.0 if self.cam_mode in (0, 1) else 0.0,
            )
        else:
            self.camera.clear_follow()

    def _cycle_camera_mode(self):
        self.cam_mode = (self.cam_mode + 1) % len(self.CAMERA_MODES)
        if self.cam_mode in (0, 2):
            self.camera.dead_zone = (120, 100)
        else:
            self.camera.dead_zone = None
        self._apply_follow()

    def make_overlay(self):
        self.overlay = OverlayScene(self.game, center=(640, 300))
        return self.overlay

    # -- input -----------------------------------------------------------

    def _read_input(self):
        held = set()
        for name in (pydex_ge.Keys.LEFT, pydex_ge.Keys.RIGHT, pydex_ge.Keys.UP, pydex_ge.Keys.DOWN):
            if self.game.input.is_key_down(name):
                held.add(name)
        self.player.held = held
        if self.game.input.is_key_pressed(pydex_ge.Keys.SPACE):
            self.player.jump_pressed = True
        if self.game.input.is_key_pressed(pydex_ge.Keys.R):
            self.player.spinning = not self.player.spinning
            print("spin", "on" if self.player.spinning else "off")
        if self.game.input.is_key_pressed(pydex_ge.Keys.EQUALS):
            self.camera.zoom = min(2.5, self.camera.zoom * 1.25)
        if self.game.input.is_key_pressed(pydex_ge.Keys.MINUS):
            self.camera.zoom = max(0.5, self.camera.zoom / 1.25)
        if self.game.input.is_key_pressed(pydex_ge.Keys.G):
            self._cycle_camera_mode()
            print("camera mode", self.CAMERA_MODES[self.cam_mode])
        if self.game.input.is_key_pressed(pydex_ge.Keys.F):
            self.follow_on = not self.follow_on
            self._apply_follow()
            print("follow", self.follow_on)
        if self.game.input.is_key_pressed(pydex_ge.Keys.C):
            self.camera.shake(12, 0.5)
            print("shake!")
        if self.game.input.is_key_pressed(pydex_ge.Keys.T):
            self.orb.cycle_tint()
            self.player.sprite.flash(0.4)
            print("tint", self.orb.sprite.tint)
        if self.game.input.is_key_pressed(pydex_ge.Keys.P):
            if len(self.game.scenes) == 1:
                self.game.scenes.push(self.make_overlay())
                print("pushed overlay (stack=%d)" % len(self.game.scenes))
            else:
                self.game.scenes.pop()
                print("popped overlay (stack=%d)" % len(self.game.scenes))
        if self.game.input.is_key_pressed(pydex_ge.Keys.ESCAPE):
            self.game.close()

    def _demo_actions(self):
        t = self.game._elapsed
        if 3.5 <= t < 3.55:
            self.camera.shake(12, 0.5)
        if 4.0 <= t < 4.05:
            self.player.spinning = True
        if 5.5 <= t < 5.55:
            self.player.spinning = False
        if 6.0 <= t < 6.05:
            self._cycle_camera_mode()
        if 6.3 <= t < 6.35:
            self._cycle_camera_mode()
        if 6.7 <= t < 6.75:
            self.orb.cycle_tint()
        if 6.85 <= t < 6.9:
            self.orb.cycle_tint()
        if 7.0 <= t < 7.05:
            self.camera.zoom = 1.6
        if 7.4 <= t < 7.45:
            self.camera.zoom = 0.9
        if 14.2 <= t < 14.25:
            self.player.spinning = True

    # -- hooks -----------------------------------------------------------

    def update(self, dt):
        if self.game.demo:
            self._demo_actions()
        else:
            self._read_input()
        super().update(dt)
        self.camera.update(dt)

    def draw(self, renderer):
        super().draw(renderer)
        player = self.player
        cam = self.camera
        pos_match = player.sprite.world_position.distance(player.body.position) < 1.0
        status = "PASS" if pos_match else "FAIL"
        status_col = (90, 255, 120) if pos_match else (255, 60, 60)
        current = self.game.scenes.current
        scene_name = current.__class__.__name__ if current is not None else "none"

        self._labels[0].text = (
            "SCENE %s  stack=%d  CAM(%s,%.2f) dead=%s follow=%s smooth=%s"
            % (
                scene_name,
                len(self.game.scenes),
                self.CAMERA_MODES[self.cam_mode],
                cam.zoom,
                cam.dead_zone is not None,
                self.follow_on,
                self.cam_mode in (0, 1),
            )
        )
        self._labels[1].text = (
            "PLAYER pos(%.0f,%.0f) vel(%.0f,%.0f) ground=%s anim=%s"
            % (
                player.body.position.x,
                player.body.position.y,
                player.body.velocity.x,
                player.body.velocity.y,
                player.on_ground,
                player.animation,
            )
        )
        self._labels[2].text = (
            "CAM pos(%.0f,%.0f) zoom=%.2f shake=(%.1f,%.1f) active=%s spin=%s"
            % (
                cam.x,
                cam.y,
                cam.zoom,
                cam.shake_offset[0],
                cam.shake_offset[1],
                cam.shaking,
                player.spinning,
            )
        )
        self._labels[3].text = (
            "ORB tint=%s ring rot=%.0f ghost alpha=%.0f"
            % (self.orb.sprite.tint, self.orb.ring.rotation % 360, self.ghost.sprite.alpha)
        )
        self._labels[4].text = (
            "ASSETS cached=%d tile_sheet=%s"
            % (len(self.game.assets), self.game.cache_ok)
        )
        self._labels[5].text = "SANITY sprite_pos==body_pos  %s" % status
        self._labels[5].color = status_col
        self._labels[6].text = (
            "arrows move | SPACE jump | R spin | +/- zoom | G camera | F follow | "
            "C shake | T tint | P overlay | ESC quit"
        )
        for label in self._labels:
            renderer.draw_label(label)


class ZooNode:
    def __init__(self, parent, offset, color, size, rot_speed, z, scale_wave=None):
        self.transform = pydex_ge.Transform2D(position=offset, parent=parent)
        self.sprite = pydex_ge.Sprite.from_pixels(size, size, _rgba_bytes(*color, 255, size * size))
        self.sprite.parent = self.transform
        self.sprite.origin = (0.5, 0.5)
        self.sprite.z = z
        self.rot_speed = rot_speed
        self.scale_wave = scale_wave
        self._phase = 0.0

    def update(self, dt):
        self.transform.rotation += self.rot_speed * dt
        if self.scale_wave is not None:
            self._phase += dt
            base, amp, freq = self.scale_wave
            s = base + amp * (0.5 + 0.5 * math.sin(self._phase * freq))
            self.sprite.scale = (s, s)
        self.sprite.update(dt)

    def draw(self, renderer):
        renderer.draw_sprite(self.sprite)


class OverlayScene(pydex_ge.Scene):
    """Transform-zoo overlay: parent/child world transforms, z-order, effects.

    Pushed on top of the play scene (suspending it), then auto-pops after
    four seconds or when ``P`` is pressed again.
    """

    def __init__(self, game, center=(640, 300)):
        super().__init__()
        self.game = game
        self._age = 0.0
        self.camera = pydex_ge.Camera2D(SCREEN_W, SCREEN_H, position=center)
        self.camera.follow(center, smoothing=0)

        root = pydex_ge.Transform2D(position=center)
        self.root = root
        a = ZooNode(root, (0, 0), (255, 90, 90), 40, 90, 1, scale_wave=(1.0, 0.6, 2.0))
        b = ZooNode(a.transform, (90, 0), (90, 255, 130), 24, 200, 3)
        c = ZooNode(b.transform, (55, 0), (120, 150, 255), 14, 320, 5)
        d = ZooNode(root, (0, 0), (255, 220, 90), 18, -140, 7)
        self.nodes = [a, b, c, d]
        self.nodes.append(ZooNode(root, (0, -110), (230, 120, 220), 16, 60, 2, scale_wave=(1.0, 0.4, 3.0)))
        for node in self.nodes:
            self.add(node)

        self._t = 0.0
        self._flash = False
        self._font = pydex_ge.Font(size=16)
        self._label = pydex_ge.Label("", font=self._font, position=(12, 12), color=(255, 240, 90))

    def on_enter(self):
        print("OverlayScene entered (transform zoo)")
        super().on_enter()

    def on_exit(self):
        print("OverlayScene exited (back to play)")
        super().on_exit()

    def update(self, dt):
        self._age += dt
        self._t += dt
        if not self.game.demo and self.game.input.is_key_pressed(pydex_ge.Keys.P):
            self.manager.pop()
            return
        if self.game.input.is_key_pressed(pydex_ge.Keys.ESCAPE):
            self.game.close()
            return
        if self._age >= 4.0:
            self.manager.pop()
            return
        self.camera.zoom = 1.0 + 0.12 * (0.5 + 0.5 * math.sin(self._t))
        super().update(dt)
        self.camera.update(dt)
        self._label.text = (
            "OverlayScene - transform zoo (parented chain a->b->c, z 1/3/5/7)"
        )

    def draw(self, renderer):
        super().draw(renderer)
        if self._flash:
            renderer.draw.rect(0, 0, SCREEN_W, SCREEN_H, color=(255, 255, 255))
        renderer.draw_label(self._label)


class Part12TestGame(pydex_ge.Game):
    def __init__(self, demo=False):
        super().__init__("PYDEX Part 12 integrated manual test", SCREEN_W, SCREEN_H, fps=60)
        self.demo = demo
        self._elapsed = 0.0
        self.demo_held = set()
        self.demo_jump_pressed = False
        self.cache_ok = False
        self._demo_pushed = False
        self._demo_replaced = False

        self.assets = pydex_ge.Assets(backend=self._backend)
        self.tileset_path = os.path.join(tempfile.gettempdir(), "pydex_part12_temp_sheet.png")
        with open(self.tileset_path, "wb") as handle:
            handle.write(_tile_sheet_bytes())

        tile_image = self.assets.image(self.tileset_path)
        self.cache_ok = self.assets.image(self.tileset_path) is tile_image
        tile_sheet = self.assets.sprite_sheet(self.tileset_path, 32, 32)

        self.tilemap = pydex_ge.TileMap(40, 24, tile_size=(32, 32))
        self.tilemap.sprite_sheet = tile_sheet
        self.tilemap.set_solid(1)
        self.tilemap.set_solid(2)
        self._build_level()

        self.play = PlayScene(self)
        self.scenes.push(self.play)

        print("PYDEX Part 12 integrated manual test.")
        print(
            "Controls: arrows move, SPACE jump, R spin, +/- zoom, G camera, "
            "F follow, C shake, T tint, P overlay, ESC quit."
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

    def update(self, dt):
        self._elapsed += dt
        if not self.demo:
            return
        t = self._elapsed
        if t < 4:
            self.demo_held = {pydex_ge.Keys.RIGHT}
        elif t < 7:
            self.demo_held = {pydex_ge.Keys.LEFT}
        elif t < 8:
            self.demo_held = {pydex_ge.Keys.RIGHT, pydex_ge.Keys.UP}
        else:
            self.demo_held = set()
        self.demo_jump_pressed = any(a <= t < a + 0.05 for a in (0.5, 3.0, 6.0))
        if 14 <= t:
            self.demo_held = {pydex_ge.Keys.RIGHT}
        if t >= 8 and not self._demo_pushed:
            self.scenes.push(self.play.make_overlay())
            self._demo_pushed = True
            print("demo: pushed overlay")
        if t >= 10 and self._demo_pushed and not self._demo_replaced:
            self.scenes.replace(self.play.make_overlay())
            self._demo_replaced = True
            print("demo: replaced overlay")
        if t >= 15:
            print("Demo complete - closing window.")
            self.close()


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
    ok += 1

    # 2. Sprite transforms
    sprite = pydex_ge.Sprite.from_pixels(16, 16, _rgba_bytes(255, 255, 255, 255, 256))
    sprite.rotation = 90
    sprite.origin = (0.5, 0.5)
    sprite.flip_x = True
    sprite.scale = (2, 1)
    assert sprite.rotation == 90.0 and sprite.origin == (0.5, 0.5)
    assert sprite.flip_x and sprite.scale == (2.0, 1.0)
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
    assert angle == 45.0 and center == (16, 8) and color_mod == (255, 0, 0)
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
    scene.add(_Track("plain"))
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
    target.x = 60
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
    assert first.shake_offset == (0.0, 0.0) and not first.shaking
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
    assert body.position == Vector2(40, 32)
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

    # 12. SceneManager lifecycle: push / pop / replace / clear
    from pydex_ge.scene.manager import SceneManager

    calls = []

    class _A(pydex_ge.Scene):
        def on_enter(self):
            calls.append("a+")

        def on_exit(self):
            calls.append("a-")

    class _B(pydex_ge.Scene):
        def on_enter(self):
            calls.append("b+")

        def on_exit(self):
            calls.append("b-")

    mgr = SceneManager()
    a, b = _A(), _B()
    mgr.push(a)
    assert mgr.current is a and len(mgr) == 1
    mgr.push(b)
    assert mgr.current is b
    mgr.pop()
    assert mgr.current is a
    mgr.replace(b)
    assert mgr.current is b
    mgr.clear()
    assert len(mgr) == 0
    assert calls == ["a+", "b+", "b-", "a-", "b+", "b-"], calls
    ok += 1

    # 13. Assets caching: image + sprite sheet share the image
    assets = pydex_ge.Assets(backend=NullBackend())
    img1 = assets.image(path)
    img2 = assets.image(path)
    assert img1 is img2
    sheet1 = assets.sprite_sheet(path, 32, 32)
    sheet2 = assets.sprite_sheet(path, 32, 32)
    assert sheet1 is sheet2 and sheet1.image is img1
    assert assets.contains(path)
    assert len(assets) == 2  # image + sheet
    assert assets.remove(path) >= 1
    ok += 1

    # 14. Coordinate roundtrip with shake (visual-only correctness)
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

    # 15. Public exports
    for name in ("Transform2D", "TileMap", "Parallax", "Assets", "SceneManager"):
        assert hasattr(pydex_ge, name), name
    from pydex_ge.graphics import Fade as GFade
    from pydex_ge.graphics import Flash as GFlash
    from pydex_ge.graphics import Tint as GTint

    assert GFade is Fade and GFlash is Flash and GTint is Tint
    ok += 1

    print(f"All {ok} Part 12 integrated checks passed.")


def main():
    if "--check" in sys.argv:
        run_checks()
        return
    Part12TestGame(demo="--demo" in sys.argv).run()
    print("Game exited cleanly.")


if __name__ == "__main__":
    main()
