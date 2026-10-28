"""PYDEX Part 3D example: two spinning cubes on a lit grid under a 3D camera.

Opens a real SDL2 window and renders 3D entirely on the CPU:

* two rotating :class:`~pydex_ge.graphics.mesh.Mesh.cube` cubes lit by a
  :class:`~pydex_ge.graphics.light.DirectionalLight`,
* a ground grid drawn with :meth:`Renderer.draw_line_3d`,
* a perspective :class:`~pydex_ge.core.camera3d.Camera3D` you fly around, and
* a HUD showing camera position, look angles, FOV, and FPS.

This example drives the renderer directly (``begin_3d``/``draw_mesh``/
``end_3d``) so the HUD labels stay in screen space on top of the 3D scene.
The same objects work inside a ``Scene(camera3d=...)`` — see
``examples/manual_3d_test.py``.

Controls
--------
* **WASD** — move forward/back/strafe (camera-relative).
* **Space / Shift** — move up / down.
* **Arrow keys** — look around (yaw/pitch).
* **Q / E** — narrow / widen the vertical FOV.
* **R** — reset the camera and cubes.
* **ESC** — quit.

Run with:  python examples/3d_basic.py
"""

from __future__ import annotations

import math

import pydex_ge


class Game3D(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX 3D Foundation", 900, 600, fps=60)
        self.background = (16, 18, 24)

        # -- camera --------------------------------------------------------
        self.camera = pydex_ge.Camera3D()
        self.camera.position = (0, 3, 10)
        self.yaw = 0.0
        self.pitch = -8.0
        self._apply_look()

        # -- light ---------------------------------------------------------
        self.light = pydex_ge.DirectionalLight(direction=(0.6, -1, 0.8), intensity=0.9, ambient=0.35)

        # -- cubes ---------------------------------------------------------
        self.cube_mesh = pydex_ge.Mesh.cube(size=2)
        self.cube = pydex_ge.Transform3D(position=(0, 0, 0))
        self.material_a = pydex_ge.Material(color=(230, 120, 60), emission=(15, 6, 0))
        self.material_b = pydex_ge.Material(color=(80, 160, 220), emission=(0, 10, 20))
        self.spin = 0.0
        self.orbit_angle = 0.0
        self.orbit = pydex_ge.Transform3D(position=(3.5, 1.5, -1.5))

        # -- ground grid (lines on the y = 0 plane) ------------------------
        self.grid: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        for i in range(-7, 8, 2):
            self.grid.append(((float(i), 0.0, -7.0), (float(i), 0.0, 7.0)))
            self.grid.append(((-7.0, 0.0, float(i)), (7.0, 0.0, float(i))))

        # -- HUD -----------------------------------------------------------
        font = pydex_ge.Font(size=16)
        small = pydex_ge.Font(size=13)
        self.hint = pydex_ge.Label(
            "WASD move   Space/Shift up/down   arrows look   Q/E fov   R reset   ESC quit",
            font=small,
            position=(12, 12),
            color=(120, 140, 165),
        )
        self.camera_info = pydex_ge.Label(
            "camera (0, 3, 10) yaw 0 pitch -8 fov 60 objects 2 (24 tris) fps 60",
            font=font,
            position=(12, 36),
            color=(220, 230, 245),
        )

    # -- helpers -----------------------------------------------------------

    def _apply_look(self) -> None:
        self.camera.rotation = pydex_ge.Quaternion.from_euler(self.yaw, self.pitch, 0.0)

    def _reset(self) -> None:
        self.camera.position = (0, 3, 10)
        self.yaw = 0.0
        self.pitch = -8.0
        self.camera.fov = 60
        self.camera.zoom = 1.0
        self.spin = 0.0
        self.orbit_angle = 0.0
        self._apply_look()

    # -- loop hooks --------------------------------------------------------

    def update(self, dt: float) -> None:
        # Camera movement (camera-relative).
        speed = 6.0 * dt
        forward = self.camera.forward
        right = self.camera.right
        horizontal = (forward.x ** 2 + forward.z ** 2) ** 0.5
        if horizontal > 1e-6:
            fx, fz = forward.x / horizontal, forward.z / horizontal
        else:
            fx, fz = 0.0, -1.0
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

        # Look around.
        if self.input.is_key_down("up"):
            self.pitch -= 60 * dt
        if self.input.is_key_down("down"):
            self.pitch += 60 * dt
        if self.input.is_key_down("left"):
            self.yaw -= 60 * dt
        if self.input.is_key_down("right"):
            self.yaw += 60 * dt
        self._apply_look()

        # FOV.
        if self.input.is_key_pressed("q"):
            self.camera.fov = max(20.0, self.camera.fov - 5)
        if self.input.is_key_pressed("e"):
            self.camera.fov = min(110.0, self.camera.fov + 5)

        # Spin the center cube; orbit the second cube around it.
        self.spin += 45 * dt
        self.orbit_angle += 30 * dt
        self.cube.rotation_euler = (self.spin, self.spin * 0.7, self.spin * 0.3)
        self.orbit.position = (
            3.5 * math.cos(math.radians(self.orbit_angle)),
            1.5 + 0.6 * math.sin(math.radians(self.orbit_angle * 1.7)),
            3.5 * math.sin(math.radians(self.orbit_angle)),
        )
        self.orbit.rotation_euler = (self.spin * 1.4, 0.0, self.spin * 0.5)

        if self.input.is_key_pressed("r"):
            self._reset()
        if self.input.is_key_pressed("escape"):
            self.close()

        self.camera_info.text = (
            f"camera ({self.camera.x:.1f}, {self.camera.y:.1f}, {self.camera.z:.1f}) "
            f"yaw {self.yaw:.0f} pitch {self.pitch:.0f} "
            f"fov {self.camera.fov:.0f} "
            f"objects 2 ({self.cube_mesh.triangle_count} tris) "
            f"fps {self.clock.fps:.0f}"
        )

    def draw(self) -> None:
        self.renderer.begin_3d(self.camera, self.light)
        for start, end in self.grid:
            self.renderer.draw_line_3d(start, end, color=(45, 55, 75))
        self.renderer.draw_mesh(self.cube_mesh, self.cube, self.material_a)
        self.renderer.draw_mesh(self.cube_mesh, self.orbit, self.material_b)
        self.renderer.end_3d()

        self.renderer.draw_label(self.hint)
        self.renderer.draw_label(self.camera_info)


def main() -> None:
    game = Game3D()
    print("PYDEX 3D Foundation example - two spinning cubes on a lit grid.")
    print("WASD move, Space/Shift up/down, arrows look, Q/E fov, R reset, ESC quit.")
    game.run()
    print("Game3D closed cleanly.")


if __name__ == "__main__":
    main()
