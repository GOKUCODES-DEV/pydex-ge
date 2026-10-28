"""PYDEX field-test: Mini 3D (spinning cubes + orbiting camera).

Exercises the 3D pipeline: ``Camera3D`` (auto-orbit + free look),
``DirectionalLight``, ``Mesh.cube``, ``Material``, ``Transform3D`` and
the direct ``begin_3d`` / ``draw_mesh`` / ``end_3d`` renderer path, plus
``draw_line_3d`` for the ground grid.  The camera slowly orbits a lit
cube while a second cube circles around it.

Controls
--------
* **Arrows** — look around (auto-orbit pauses while you steer)
* **Q / E** — narrow / widen the vertical FOV
* **R** — reset the camera
* **ESC** — quit

Run with:  python games/cube3d.py
"""

from __future__ import annotations

import math

import pydex_ge


class Cube3DGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Mini 3D", 720, 540, fps=60)
        self.background = (12, 14, 22)

        self.camera = pydex_ge.Camera3D()
        self.camera.position = (0, 4, 10)
        self.yaw = 0.0
        self.pitch = -10.0
        self._apply_look()

        self.light = pydex_ge.DirectionalLight(direction=(0.6, -1, 0.8), intensity=0.9, ambient=0.35)

        self.cube_mesh = pydex_ge.Mesh.cube(size=2)
        self.center = pydex_ge.Transform3D(position=(0, 1, 0))
        self.orbiter = pydex_ge.Transform3D(position=(4, 0, 0))
        self.material_a = pydex_ge.Material(color=(230, 120, 60), emission=(15, 6, 0))
        self.material_b = pydex_ge.Material(color=(80, 160, 220), emission=(0, 10, 20))

        self.grid: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        for i in range(-8, 9, 2):
            self.grid.append(((float(i), 0.0, -8.0), (float(i), 0.0, 8.0)))
            self.grid.append(((-8.0, 0.0, float(i)), (8.0, 0.0, float(i))))

        self.hud_label = pydex_ge.Label(
            "camera (0, 4, 10) yaw 0 pitch -10 fov 60 fps 60",
            font=pydex_ge.Font(size=14),
            position=(12, 12),
            color=(220, 230, 245),
        )
        self.hint_label = pydex_ge.Label(
            "arrows: orbit   Q/E fov   R reset   ESC quit",
            font=pydex_ge.Font(size=13),
            position=(12, 34),
            color=(120, 140, 165),
        )

        self.spin = 0.0
        self.orbit_angle = 0.0

    def _apply_look(self) -> None:
        self.camera.rotation = pydex_ge.Quaternion.from_euler(self.yaw, self.pitch, 0.0)

    def _reset(self) -> None:
        self.camera.position = (0, 4, 10)
        self.yaw = 0.0
        self.pitch = -10.0
        self.camera.fov = 60
        self.camera.zoom = 1.0
        self._apply_look()

    # -- loop hooks -------------------------------------------------------

    def update(self, dt: float) -> None:
        steering = (
            self.input.is_key_down("up")
            or self.input.is_key_down("down")
            or self.input.is_key_down("left")
            or self.input.is_key_down("right")
        )
        if steering:
            if self.input.is_key_down("up"):
                self.pitch -= 55 * dt
            if self.input.is_key_down("down"):
                self.pitch += 55 * dt
            if self.input.is_key_down("left"):
                self.yaw -= 55 * dt
            if self.input.is_key_down("right"):
                self.yaw += 55 * dt
        else:
            self.yaw += 14 * dt
        self.pitch = max(-85.0, min(85.0, self.pitch))
        self._apply_look()

        if self.input.is_key_pressed("q"):
            self.camera.fov = max(20.0, self.camera.fov - 5)
        if self.input.is_key_pressed("e"):
            self.camera.fov = min(110.0, self.camera.fov + 5)
        if self.input.is_key_pressed("r"):
            self._reset()
        if self.input.is_key_pressed("escape"):
            self.close()

        self.spin += 60 * dt
        self.orbit_angle += 36 * dt
        self.center.rotation_euler = (self.spin, self.spin * 0.7, self.spin * 0.3)
        self.orbiter.position = (
            4.0 * math.cos(math.radians(self.orbit_angle)),
            1.0 + 0.8 * math.sin(math.radians(self.orbit_angle * 1.6)),
            4.0 * math.sin(math.radians(self.orbit_angle)),
        )
        self.orbiter.rotation_euler = (self.spin * 1.4, 0.0, self.spin * 0.5)

        self.hud_label.text = (
            f"camera ({self.camera.x:.1f}, {self.camera.y:.1f}, {self.camera.z:.1f}) "
            f"yaw {self.yaw:.0f} pitch {self.pitch:.0f} "
            f"fov {self.camera.fov:.0f} fps {self.clock.fps:.0f}"
        )

    def draw(self) -> None:
        self.renderer.begin_3d(self.camera, self.light)
        for start, end in self.grid:
            self.renderer.draw_line_3d(start, end, color=(40, 52, 74))
        self.renderer.draw_mesh(self.cube_mesh, self.center, self.material_a)
        self.renderer.draw_mesh(self.cube_mesh, self.orbiter, self.material_b)
        self.renderer.end_3d()

        self.renderer.draw_label(self.hud_label)
        self.renderer.draw_label(self.hint_label)


def make_game() -> pydex_ge.Game:
    return Cube3DGame()


def main() -> None:
    print("PYDEX Mini 3D - a lit cube with an orbiting companion.")
    make_game().run()
    print("Cube3DGame closed cleanly.")


if __name__ == "__main__":
    main()