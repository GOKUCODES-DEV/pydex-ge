"""Temporary interactive manual test for Part 3D: the CPU 3D Foundation.

A small fly-around scene that exercises the complete 3D subsystem at once,
the way a real game would use it, so you can verify the pieces work
together rather than in isolation:

* :class:`pydex_ge.Vector3`, :class:`pydex_ge.Quaternion`, and
  :class:`pydex_ge.Transform3D` math,
* :class:`pydex_ge.Mesh` (triangle/quad/cube), :class:`pydex_ge.Material`, and
  :class:`pydex_ge.Object3D`,
* :class:`pydex_ge.Camera3D` perspective projection and ``look_at``,
* the renderer 3D path (``begin_3d`` / ``draw_mesh`` / ``end_3d`` /
  ``draw_line_3d``) with back-face culling, depth sorting, and a
  :class:`pydex_ge.DirectionalLight`,
* :class:`pydex_ge.Scene` integration (a scene with a ``camera3d``).

Run modes::

    python examples/manual_3d_test.py --check   # headless checks, no window
    python examples/manual_3d_test.py --demo    # auto-driven windowed run
    python examples/manual_3d_test.py           # interactive windowed run

Controls::

    WASD   move (camera-relative)   Q / E   narrow / widen FOV
    Space / Shift  up / down        R       reset
    arrows  look around             ESC     quit

This file is a manual verification aid only; it is not part of the public
PYDEX API and may be deleted at any time.
"""

from __future__ import annotations

import math
import sys

import pydex_ge

SCREEN_W, SCREEN_H = 800, 600


def run_checks() -> None:
    """Headless assertions over the whole Part 3D subsystem (no window)."""
    ok = 0

    # 1. Vector3 math
    v = pydex_ge.Vector3(1, 2, 3)
    assert v == pydex_ge.Vector3(1.0, 2.0, 3.0)
    assert v + pydex_ge.Vector3(1, 1, 1) == pydex_ge.Vector3(2, 3, 4)
    assert pydex_ge.Vector3(1, 0, 0).cross(pydex_ge.Vector3(0, 1, 0)) == pydex_ge.Vector3(0, 0, 1)
    assert abs(pydex_ge.Vector3(1, 2, 2).length - 3.0) < 1e-9
    assert pydex_ge.Vector3(0, 3, 0).normalized() == pydex_ge.Vector3(0, 1, 0)
    assert abs(pydex_ge.Vector3(0, 0, 0).distance(pydex_ge.Vector3(3, 4, 0)) - 5.0) < 1e-9
    assert pydex_ge.Vector3(3, 0, 0).clamp_length(2) == pydex_ge.Vector3(2, 0, 0)
    try:
        pydex_ge.Vector3(True, 0, 0)
        raise AssertionError("bool accepted")
    except pydex_ge.ConfigurationError:
        pass
    ok += 1

    # 2. Quaternion rotation
    q = pydex_ge.Quaternion.from_euler(90, 0, 0)
    r = q.rotate_vector(pydex_ge.Vector3(0, 0, 1))
    assert abs(r.x - 1.0) < 1e-9 and abs(r.y) < 1e-9 and abs(r.z) < 1e-9
    qa = pydex_ge.Quaternion.from_axis_angle((0, 1, 0), 90)
    assert abs(qa.rotate_vector(pydex_ge.Vector3(0, 0, 1)).x - 1.0) < 1e-9
    spin = pydex_ge.Quaternion.from_euler(40, -20, 15)
    vec = pydex_ge.Vector3(2, -3, 5)
    assert spin.inverse().rotate_vector(spin.rotate_vector(vec)).distance(vec) < 1e-6
    for euler in [(0, 0, 0), (30, 20, 10), (-120, 45, 80), (90, 0, 0)]:
        back = pydex_ge.Quaternion.from_euler(*euler).to_euler()
        assert all(abs(a - b) < 1e-6 for a, b in zip(back, euler)), (euler, back)
    ok += 1

    # 3. Transform3D parenting
    parent = pydex_ge.Transform3D(position=(5, 0, 0), rotation=pydex_ge.Quaternion.from_euler(90, 0, 0))
    child = pydex_ge.Transform3D(position=(0, 0, 1), parent=parent)
    wp = child.world_position
    assert abs(wp.x - 6.0) < 1e-9 and abs(wp.y) < 1e-9 and abs(wp.z) < 1e-9
    assert abs(child.world_rotation.to_euler()[0] - 90.0) < 1e-6
    scaled = pydex_ge.Transform3D(scale=(2, 1, 1))
    child2 = pydex_ge.Transform3D(scale=(1, 3, 1), parent=scaled)
    assert child2.world_scale == pydex_ge.Vector3(2, 3, 1)
    ok += 1

    # 4. Mesh primitives
    cube = pydex_ge.Mesh.cube(size=2)
    assert cube.vertex_count == 8 and cube.triangle_count == 12
    assert len(cube.face_normals) == 12
    tri = pydex_ge.Mesh.triangle((0, 0, 0), (1, 0, 0), (0, 1, 0))
    assert tri.face_normals[0].z > 0.99
    quad = pydex_ge.Mesh.quad((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))
    assert quad.triangle_count == 2
    try:
        pydex_ge.Mesh([pydex_ge.Vector3(0, 0, 0)], [(0, 1, 2)])
        raise AssertionError("bad index accepted")
    except pydex_ge.ConfigurationError:
        pass
    ok += 1

    # 5. Material + Object3D draw forwarding
    mat = pydex_ge.Material(color=(200, 80, 40), opacity=0.5)
    assert mat.color == (200, 80, 40) and mat.opacity == 0.5
    try:
        pydex_ge.Material(color=(300, 0, 0))
        raise AssertionError("bad color accepted")
    except pydex_ge.ConfigurationError:
        pass

    class FakeRenderer:
        def __init__(self):
            self.active_camera3d = object()
            self.args = None

        def draw_mesh(self, mesh, transform, material):
            self.args = (mesh, transform, material)

    fake = FakeRenderer()
    obj = pydex_ge.Object3D(mesh=cube, material=mat)
    obj.draw(fake)
    assert fake.args is not None and fake.args[0] is cube
    hidden = pydex_ge.Object3D(mesh=cube)
    hidden.visible = False
    fake2 = FakeRenderer()
    hidden.draw(fake2)
    assert fake2.args is None
    ok += 1

    # 6. Camera3D projection and look_at
    cam = pydex_ge.Camera3D(SCREEN_W, SCREEN_H)
    cam.set_viewport(SCREEN_W, SCREEN_H)
    sx, sy, depth = cam.project((0, 0, -5))
    assert abs(sx - SCREEN_W / 2) < 1e-9 and abs(sy - SCREEN_H / 2) < 1e-9
    assert abs(depth - 5.0) < 1e-9
    assert cam.project((0, 0, 5)) is None
    assert cam.project((0, 0, -2000)) is None
    cam.look_at((10, 0, 0))
    assert abs(cam.forward.x - 1.0) < 1e-9
    sx, sy, _ = cam.project((10, 0, 0))
    assert abs(sx - SCREEN_W / 2) < 1e-6 and abs(sy - SCREEN_H / 2) < 1e-6
    cam.position = (0, 3, -8)
    cam.look_at((0, 0, 0))
    assert cam.project((0, 0, 0)) is not None
    ok += 1

    # 7. render3d pipeline: sorted triangles, lighting, raster spans
    from pydex_ge.core.render3d import build_triangles, fill_triangle, shade_color
    from pydex_ge.graphics.light import DirectionalLight

    cam2 = pydex_ge.Camera3D(SCREEN_W, SCREEN_H)
    cam2.set_viewport(SCREEN_W, SCREEN_H)
    recs = build_triangles(cam2, cube, pydex_ge.Transform3D(position=(0, 0, -6)), pydex_ge.Material(), None)
    assert len(recs) > 0
    depths = [r[4] for r in recs]
    assert depths == sorted(depths, reverse=True)
    light = DirectionalLight(direction=(0, -1, 0))
    assert shade_color(pydex_ge.Material(color=(255, 255, 255)), pydex_ge.Vector3(0, 1, 0), light) == (255, 255, 255)
    assert shade_color(pydex_ge.Material(color=(255, 255, 255)), pydex_ge.Vector3(0, -1, 0), light) == (0, 0, 0)
    lines = []
    fill_triangle(
        ((0, 0, 1), (4, 4, 1), (4, 0, 1), (255, 0, 0), 1.0),
        lambda x1, y1, x2, y2, color: lines.append((x1, y1, x2, y2, color)),
    )
    assert len(lines) > 0 and all(y1 == y2 for x1, y1, x2, y2, color in lines)
    ok += 1

    # 8. Renderer 3D path on the headless Null backend
    from pydex_ge.backend.null import NullRenderer

    renderer = pydex_ge.Renderer(NullRenderer(), size=(SCREEN_W, SCREEN_H))
    cam3 = pydex_ge.Camera3D()
    renderer.begin_3d(cam3)
    renderer.draw_mesh(cube, pydex_ge.Transform3D(position=(0, 0, -6)), pydex_ge.Material(color=(255, 0, 0)))
    renderer.draw_line_3d((0, 0, -6), (0, 0, -5), color=(0, 255, 0))
    assert renderer.active_camera3d is cam3
    renderer.end_3d()
    assert renderer.active_camera3d is None
    try:
        renderer.end_3d()
        raise AssertionError("end_3d without begin_3d accepted")
    except RuntimeError:
        pass
    ok += 1

    # 9. Scene integration: camera3d draws 3D objects; 2D scenes tolerate them
    scene = pydex_ge.Scene(camera3d=pydex_ge.Camera3D())
    scene.add(pydex_ge.Object3D(mesh=cube, transform=pydex_ge.Transform3D(position=(0, 0, -6))))
    scene2d = pydex_ge.Scene()
    scene2d.add(pydex_ge.Object3D(mesh=cube))
    scene2d.draw(pydex_ge.Renderer(NullRenderer(), size=(SCREEN_W, SCREEN_H)))
    scene.draw(pydex_ge.Renderer(NullRenderer(), size=(SCREEN_W, SCREEN_H)))
    ok += 1

    # 10. Public exports + version
    for name in ("Vector3", "Quaternion", "Transform3D", "Camera3D", "Mesh", "Material", "Object3D", "DirectionalLight"):
        assert hasattr(pydex_ge, name), name
    assert pydex_ge.__version__ == "1.0.0"
    ok += 1

    print(f"All {ok} Part 3D integrated checks passed.")


class Game3DTest(pydex_ge.Game):
    def __init__(self, demo: bool = False) -> None:
        super().__init__("PYDEX 3D Manual Test", SCREEN_W, SCREEN_H, fps=60)
        self.background = (16, 18, 24)
        self.demo = demo
        self.elapsed = 0.0

        self.camera = pydex_ge.Camera3D()
        self.camera.position = (0, 3, 10)
        self.yaw = 0.0
        self.pitch = -8.0
        self._apply_look()

        self.light = pydex_ge.DirectionalLight(direction=(0.6, -1, 0.8), intensity=0.9, ambient=0.35)

        self.cube_mesh = pydex_ge.Mesh.cube(size=2)
        self.cube = pydex_ge.Transform3D(position=(0, 0, 0))
        self.material_a = pydex_ge.Material(color=(230, 120, 60), emission=(15, 6, 0))
        self.material_b = pydex_ge.Material(color=(80, 160, 220), emission=(0, 10, 20))
        self.spin = 0.0
        self.orbit_angle = 0.0
        self.orbit = pydex_ge.Transform3D(position=(3.5, 1.5, -1.5))

        self.grid = []
        for i in range(-7, 8, 2):
            self.grid.append(((float(i), 0.0, -7.0), (float(i), 0.0, 7.0)))
            self.grid.append(((-7.0, 0.0, float(i)), (7.0, 0.0, float(i))))

        font = pydex_ge.Font(size=16)
        small = pydex_ge.Font(size=13)
        self.hint = pydex_ge.Label(
            "WASD move  Space/Shift up/down  arrows look  Q/E fov  R reset  ESC quit",
            font=small,
            position=(12, 12),
            color=(120, 140, 165),
        )
        self.status = pydex_ge.Label(
            "camera (0, 3, 10) fov 60 objects 2 (24 tris) fps 60 PASS",
            font=font,
            position=(12, 36),
            color=(220, 230, 245),
        )

    # -- helpers -----------------------------------------------------------

    def _apply_look(self) -> None:
        self.camera.rotation = pydex_ge.Quaternion.from_euler(self.yaw, self.pitch, 0.0)

    def _spin_cubes(self, dt: float) -> None:
        self.spin += 45 * dt
        self.orbit_angle += 30 * dt
        self.cube.rotation_euler = (self.spin, self.spin * 0.7, self.spin * 0.3)
        self.orbit.position = (
            3.5 * math.cos(math.radians(self.orbit_angle)),
            1.5 + 0.6 * math.sin(math.radians(self.orbit_angle * 1.7)),
            3.5 * math.sin(math.radians(self.orbit_angle)),
        )
        self.orbit.rotation_euler = (self.spin * 1.4, 0.0, self.spin * 0.5)

    # -- loop hooks --------------------------------------------------------

    def update(self, dt: float) -> None:
        self._spin_cubes(dt)
        if self.demo:
            self.elapsed += dt
            angle = self.elapsed * 0.35
            self.camera.position = (11 * math.cos(angle), 4.5, 11 * math.sin(angle))
            self.camera.look_at((0, 0, 0))
            if self.elapsed > 20:
                self.close()
        else:
            speed = 6.0 * dt
            forward = self.camera.forward
            right = self.camera.right
            horizontal = (forward.x ** 2 + forward.z ** 2) ** 0.5
            fx, fz = (forward.x / horizontal, forward.z / horizontal) if horizontal > 1e-6 else (0.0, -1.0)
            dx = dz = dy = 0.0
            if self.input.is_key_down("w"):
                dx += fx * speed
                dz += fz * speed
            if self.input.is_key_down("s"):
                dx -= fx * speed
                dz -= fz * speed
            if self.input.is_key_down("a"):
                dx -= right.x * speed
                dz -= right.z * speed
            if self.input.is_key_down("d"):
                dx += right.x * speed
                dz += right.z * speed
            if self.input.is_key_down("space"):
                dy += speed
            if self.input.is_key_down("shift"):
                dy -= speed
            self.camera.move(dx, dy, dz)

            if self.input.is_key_down("up"):
                self.pitch -= 60 * dt
            if self.input.is_key_down("down"):
                self.pitch += 60 * dt
            if self.input.is_key_down("left"):
                self.yaw -= 60 * dt
            if self.input.is_key_down("right"):
                self.yaw += 60 * dt
            self._apply_look()

        if self.input.is_key_pressed("q"):
            self.camera.fov = max(20.0, self.camera.fov - 5)
        if self.input.is_key_pressed("e"):
            self.camera.fov = min(110.0, self.camera.fov + 5)
        if self.input.is_key_pressed("r"):
            self.camera.position = (0, 3, -10)
            self.yaw = 0.0
            self.pitch = -8.0
            self.camera.fov = 60
            self._apply_look()
        if self.input.is_key_pressed("escape"):
            self.close()

        mode = "demo" if self.demo else "manual"
        self.status.text = (
            f"camera ({self.camera.x:.1f}, {self.camera.y:.1f}, {self.camera.z:.1f}) "
            f"fov {self.camera.fov:.0f} objects 2 ({self.cube_mesh.triangle_count} tris) "
            f"fps {self.clock.fps:.0f} {mode} PASS"
        )

    def draw(self) -> None:
        self.renderer.begin_3d(self.camera, self.light)
        for start, end in self.grid:
            self.renderer.draw_line_3d(start, end, color=(45, 55, 75))
        self.renderer.draw_mesh(self.cube_mesh, self.cube, self.material_a)
        self.renderer.draw_mesh(self.cube_mesh, self.orbit, self.material_b)
        self.renderer.end_3d()

        self.renderer.draw_label(self.hint)
        self.renderer.draw_label(self.status)


def main() -> None:
    if "--check" in sys.argv:
        run_checks()
        return
    Game3DTest(demo="--demo" in sys.argv).run()
    print("Game exited cleanly.")


if __name__ == "__main__":
    main()
