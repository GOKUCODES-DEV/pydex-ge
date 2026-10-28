"""Temporary manual test for Part 8: Camera2D, zoom, and world-to-screen.

A triangle (drawn from three rotated world-space vertices) moves with the
arrow keys, spins while ``R`` is active, and is followed by a
:class:`pydex_ge.Camera2D` (zoom ``+``/``-``).  World sprites and a grid are
drawn through the camera; labels and a crosshair are drawn after
``end_camera()`` to prove UI stays screen-space.

Run modes::

    python examples/manual_camera_test.py --check   # headless math checks, no window
    python examples/manual_camera_test.py --demo    # auto-driven windowed run
    python examples/manual_camera_test.py           # interactive windowed run

This file is a manual verification aid only; it is not part of the public
PYDEX API and may be deleted at any time.
"""

from __future__ import annotations

import pydex_ge
from pydex_ge.physics import Rect, Vector2

WORLD = Rect(0, 0, 2000, 1200)
PLAY = Rect(24, 24, 1952, 1152)
SCREEN_W, SCREEN_H = 800, 600


def _rgba_bytes(r, g, b, a, count):
    return bytes((r, g, b, a)) * count


class TriangleTestGame(pydex_ge.Game):
    def __init__(self, demo=False):
        super().__init__("PYDEX Part 8 manual test", SCREEN_W, SCREEN_H, fps=60)
        self.demo = demo
        self._elapsed = 0.0
        self._last_report = 0.0
        self._demo_held = set()

        self.pos = Vector2(400, 900)
        self.angle = 0.0
        self.spinning = False
        self._local = (Vector2(0, -20), Vector2(15, 14), Vector2(-15, 14))

        self.camera = pydex_ge.Camera2D(SCREEN_W, SCREEN_H, position=(400, 900))
        self.camera.bounds = WORLD
        self.camera.follow(self.pos, smoothing=4.0)
        self.follow_on = True
        self.smoothing_on = True

        self._font = pydex_ge.Font(size=16)
        self._labels = [
            pydex_ge.Label("", font=self._font, position=(12, 10 + i * 20), color=(240, 240, 240))
            for i in range(4)
        ]
        self._world_sprites = self._build_world()

        print("PYDEX Part 8 manual test.")
        print("Controls: arrows move, R spin, +/- zoom, G toggle smoothing, F toggle follow, ESC quit.")
        print("Demo mode on." if demo else "Interactive mode.")

    def _build_world(self):
        floor = pydex_ge.Sprite.from_pixels(2000, 40, _rgba_bytes(24, 70, 34, 255, 2000 * 40))
        floor.position = (0, 1160)
        wall_l = pydex_ge.Sprite.from_pixels(40, 1200, _rgba_bytes(30, 84, 40, 255, 40 * 1200))
        wall_l.position = (0, 0)
        wall_r = pydex_ge.Sprite.from_pixels(40, 1200, _rgba_bytes(30, 84, 40, 255, 40 * 1200))
        wall_r.position = (1960, 0)
        markers = []
        for cx in range(0, 2001, 200):
            for cy in range(0, 1201, 200):
                m = pydex_ge.Sprite.from_pixels(8, 8, _rgba_bytes(120, 120, 150, 255, 64))
                m.position = (cx - 4, cy - 4)
                markers.append(m)
        return [floor, wall_l, wall_r] + markers

    def _demo_step(self):
        t = self._elapsed
        if t < 3:
            self._demo_held = {pydex_ge.Keys.RIGHT}
        elif t < 6:
            self._demo_held = {pydex_ge.Keys.LEFT}
        elif t < 9:
            self._demo_held = {pydex_ge.Keys.UP}
        else:
            self._demo_held = set()
        if t >= 9:
            self.spinning = True
        if 12 <= t < 14:
            self.camera.zoom = 1.0 + (t - 12.0) * 0.6
        if 15 <= t < 17:
            self.camera.zoom = 2.2 - (t - 15.0) * 0.6
        if t >= 20:
            print("Demo complete - closing window.")
            self.close()

    def _read_input(self):
        held = set()
        for name in (pydex_ge.Keys.LEFT, pydex_ge.Keys.RIGHT, pydex_ge.Keys.UP, pydex_ge.Keys.DOWN):
            if self.input.is_key_down(name):
                held.add(name)
        return held

    def _toggle_follow(self):
        if self.follow_on:
            self.camera.follow(self.pos, smoothing=4.0 if self.smoothing_on else 0.0)
        else:
            self.camera.clear_follow()

    def update(self, dt):
        self._elapsed += dt
        if self.demo:
            self._demo_step()
            held = self._demo_held
        else:
            held = self._read_input()
            if self.input.is_key_pressed(pydex_ge.Keys.R):
                self.spinning = not self.spinning
            if self.input.is_key_pressed(pydex_ge.Keys.EQUALS):
                self.camera.zoom = min(2.5, self.camera.zoom * 1.25)
            if self.input.is_key_pressed(pydex_ge.Keys.MINUS):
                self.camera.zoom = max(0.5, self.camera.zoom / 1.25)
            if self.input.is_key_pressed(pydex_ge.Keys.G):
                self.smoothing_on = not self.smoothing_on
                self._toggle_follow()
            if self.input.is_key_pressed(pydex_ge.Keys.F):
                self.follow_on = not self.follow_on
                self._toggle_follow()
            if self.input.is_key_pressed(pydex_ge.Keys.ESCAPE):
                self.close()

        speed = 300.0
        if pydex_ge.Keys.LEFT in held:
            self.pos.x -= speed * dt
        if pydex_ge.Keys.RIGHT in held:
            self.pos.x += speed * dt
        if pydex_ge.Keys.UP in held:
            self.pos.y -= speed * dt
        if pydex_ge.Keys.DOWN in held:
            self.pos.y += speed * dt
        self.pos.x = min(max(self.pos.x, PLAY.left), PLAY.right)
        self.pos.y = min(max(self.pos.y, PLAY.top), PLAY.bottom)

        if self.spinning:
            self.angle += 90.0 * dt

        self.camera.update(dt)

        self._last_report += dt
        if self._last_report >= 1.0:
            self._last_report = 0.0
            off = self.pos - self.camera.position
            print(
                "t=%6.2f pos=(%7.1f,%7.1f) cam=(%7.1f,%7.1f) off=(%6.1f,%6.1f) "
                "zoom=%.2f spin=%s follow=%s smooth=%s"
                % (self._elapsed, self.pos.x, self.pos.y, self.camera.x, self.camera.y,
                   off.x, off.y, self.camera.zoom, self.spinning, self.follow_on, self.smoothing_on),
                flush=True,
            )

    def draw(self):
        r = self.renderer
        r.clear((18, 18, 24))

        r.begin_camera(self.camera)
        for sprite in self._world_sprites:
            r.draw_sprite(sprite)
        grid_col = (45, 45, 56)
        for x in range(0, 2001, 200):
            a = self.camera.world_to_screen((x, 0))
            b = self.camera.world_to_screen((x, 1200))
            r.draw.line(round(a.x), round(a.y), round(b.x), round(b.y), color=grid_col)
        for y in range(0, 1201, 200):
            a = self.camera.world_to_screen((0, y))
            b = self.camera.world_to_screen((2000, y))
            r.draw.line(round(a.x), round(a.y), round(b.x), round(b.y), color=grid_col)

        verts = [self.pos + v.rotate(self.angle) for v in self._local]
        pts = [self.camera.world_to_screen(v) for v in verts]
        tri_col = (255, 90, 60)
        for i in range(3):
            p1, p2 = pts[i], pts[(i + 1) % 3]
            x1, y1, x2, y2 = round(p1.x), round(p1.y), round(p2.x), round(p2.y)
            r.draw.line(x1, y1, x2, y2, color=tri_col)
            r.draw.line(x1 + 1, y1, x2 + 1, y2, color=tri_col)
            r.draw.line(x1, y1 + 1, x2, y2 + 1, color=tri_col)
        pivot = self.camera.world_to_screen(self.pos)
        r.draw.rect(round(pivot.x) - 3, round(pivot.y) - 3, 6, 6, color=(255, 240, 90))
        tip = self.camera.world_to_screen(verts[0])
        r.draw.circle(round(tip.x), round(tip.y), 4, color=(255, 255, 255))
        r.end_camera()

        r.draw.line(SCREEN_W // 2, 265, SCREEN_W // 2, 335, color=(255, 255, 255))
        r.draw.line(365, SCREEN_H // 2, 435, SCREEN_H // 2, color=(255, 255, 255))
        for sx in range(0, SCREEN_W + 1, 25):
            r.draw.line(sx, 588, sx, SCREEN_H, color=(70, 70, 90))

        self._labels[0].text = (
            f"TRI world ({self.pos.x:.0f}, {self.pos.y:.0f})  "
            f"angle {self.angle:5.1f}  spin {'ON' if self.spinning else 'off'}"
        )
        self._labels[1].text = (
            f"CAM world ({self.camera.x:.0f}, {self.camera.y:.0f})  "
            f"offset ({(self.pos.x - self.camera.x):.0f}, {(self.pos.y - self.camera.y):.0f})"
        )
        self._labels[2].text = (
            f"ZOOM {self.camera.zoom:.2f}  follow {self.follow_on}  "
            f"smoothing {self.smoothing_on}"
        )
        self._labels[3].text = "arrows move | R spin | +/- zoom | G smoothing | F follow | ESC quit"
        for label in self._labels:
            r.draw_label(label)


def run_checks():
    ok = 0
    cam = pydex_ge.Camera2D(SCREEN_W, SCREEN_H, position=(400, 300), zoom=1.0)
    for wx, wy in ((0, 0), (400, 300), (123.5, -77.25), (2000, 1200)):
        screen = cam.world_to_screen((wx, wy))
        back = cam.screen_to_world(screen)
        assert abs(back.x - wx) < 1e-6 and abs(back.y - wy) < 1e-6
        ok += 1
    cam.zoom = 2.0
    a = cam.world_to_screen((100, 100))
    b = cam.world_to_screen((200, 100))
    assert abs((b.x - a.x) - 200) < 1e-9
    ok += 1
    cam.zoom = 0.5
    a = cam.world_to_screen((100, 100))
    b = cam.world_to_screen((200, 100))
    assert abs((b.x - a.x) - 50) < 1e-9
    ok += 1
    cam.position = (555, 777)
    cam.zoom = 1.5
    center = cam.world_to_screen((555, 777))
    assert abs(center.x - SCREEN_W / 2) < 1e-9 and abs(center.y - SCREEN_H / 2) < 1e-9
    ok += 1

    target = Vector2(900, 500)
    cam = pydex_ge.Camera2D(SCREEN_W, SCREEN_H, position=(0, 0))
    cam.follow(target, smoothing=0)
    cam.update(0.016)
    assert cam.position == target
    ok += 1
    cam = pydex_ge.Camera2D(SCREEN_W, SCREEN_H, position=(0, 0))
    cam.follow(target, smoothing=4.0)
    cam.update(0.016)
    assert 0 < cam.x < 900
    for _ in range(2000):
        cam.update(0.016)
    assert abs(cam.x - 900) < 1.0 and abs(cam.y - 500) < 1.0
    ok += 1

    cam = pydex_ge.Camera2D(SCREEN_W, SCREEN_H, position=(0, 0))
    cam.bounds = WORLD
    cam.follow((1000, 1200), smoothing=0)
    cam.update(0.016)
    assert cam.x == 1000 and cam.y == 900, (cam.x, cam.y)
    ok += 1

    pos = Vector2(500, 500)
    local = (Vector2(0, -20), Vector2(15, 14), Vector2(-15, 14))
    for degrees in (0, 45, 90, 180, 360):
        for vec in local:
            rotated = vec.rotate(degrees)
            assert abs(rotated.length - vec.length) < 1e-9
            assert pos.distance(pos + rotated) <= 40
        ok += 1

    print(f"All {ok} Part 8 checks passed.")


def main():
    import sys

    if "--check" in sys.argv:
        run_checks()
        return
    TriangleTestGame(demo="--demo" in sys.argv).run()
    print("Game exited cleanly.")


if __name__ == "__main__":
    main()
