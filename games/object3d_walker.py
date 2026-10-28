"""PYDEX field-test: Object 3D Walker (scene + Object3D + Text HUD).

Exercises ``Object3D`` nodes (mesh + material + transform, ``move``,
``rotation_euler``), a ``Scene`` driven through ``camera3d`` + light while
the HUD is drawn with ``Text`` via ``renderer.draw_text`` in screen space,
and a third-person camera that follows the walker with ``look_at``.
Collect the floating gems, dodge the pillars.

Controls
--------
* **Left / Right** — turn
* **Up / Down** — walk forward / back (camera follows behind)
* **SPACE** — hopping bounce
* **R** — reset the walker to the start
* **ESC** — quit

Run with:  python games/object3d_walker.py
"""

from __future__ import annotations

import math

import pydex_ge

W, H = 800, 600
SPEED = 6.0
TURN_SPEED = 90.0
BOUNDS = 24.0


class WalkerGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Object 3D Walker", W, H, fps=60)
        self.background = (10, 12, 20)

        self.camera = pydex_ge.Camera3D()
        self.camera.position = (0, 5, 12)
        self.camera.fov = 65
        self.light = pydex_ge.DirectionalLight(direction=(0.5, -0.9, 0.7), intensity=0.9, ambient=0.35)

        self.scenes.push(WalkerScene(self))

    def close(self) -> None:
        super().close()


class WalkerScene(pydex_ge.Scene):
    def __init__(self, game) -> None:
        super().__init__(camera3d=game.camera, light=game.light)
        self.game = game
        self.camera = game.camera

        self.player = pydex_ge.Object3D(
            mesh=pydex_ge.Mesh.cube(size=1.0),
            material=pydex_ge.Material(color=(235, 125, 60), emission=(14, 5, 0)),
        )
        self.player.position = (0, 1.0, 0)

        gem_mesh = pydex_ge.Mesh.cube(size=0.6)
        gem_mats = [
            pydex_ge.Material(color=(90, 200, 255), emission=(0, 12, 24)),
            pydex_ge.Material(color=(140, 255, 150), emission=(0, 18, 8)),
            pydex_ge.Material(color=(255, 220, 120), emission=(16, 10, 0)),
        ]
        self.gems = []
        for index, (pos, mat) in enumerate(zip(
            ((9.0, 1.4, 8.0), (-11.0, 1.6, -6.0), (12.0, 1.2, -12.0)), gem_mats
        )):
            gem = pydex_ge.Object3D(mesh=gem_mesh, material=mat)
            gem.position = pos
            self.gems.append(gem)

        pillar_mesh = pydex_ge.Mesh.cube(size=1.1)
        pillar_mat = pydex_ge.Material(color=(150, 130, 110), emission=(4, 2, 0))
        self.pillars = []
        for pos in ((-8.0, 0.0, 10.0), (7.0, 0.0, -9.0), (-14.0, 0.0, -14.0),
                    (15.0, 0.0, 6.0), (0.0, 0.0, 16.0), (-6.0, 0.0, -16.0)):
            pillar = pydex_ge.Object3D(mesh=pillar_mesh, material=pillar_mat)
            pillar.position = pos
            self.pillars.append(pillar)

        self.nodes = [self.player, *self.gems, *self.pillars]
        self.yaw = 0.0
        self.hop = 0.0
        self.gems_left = len(self.gems)
        self.elapsed = 0.0
        self._prev_pos = (0.0, 0.0, 0.0)

        self.hud = pydex_ge.Text(
            "gems 3   walker (0, 1, 0)", font=pydex_ge.Font(size=14),
            position=(12, 12), color=(220, 230, 245),
        )
        self.hint = pydex_ge.Text(
            "Arrows: turn/walk   SPACE: hop   R: reset   ESC: quit",
            font=pydex_ge.Font(size=12), position=(12, 32), color=(120, 140, 165),
        )

        self.reset()

    def reset(self) -> None:
        self.player.position = (0, 1.0, 0)
        self.yaw = 0.0
        self.gems_left = len(self.gems)
        for gem in self.gems:
            gem.visible = True

    def update(self, dt: float) -> None:
        super().update(dt)
        self.elapsed += dt

        # Turn with left/right, walk along the facing direction.
        if self.game.input.is_key_down("left"):
            self.yaw += math.radians(TURN_SPEED * dt)
        if self.game.input.is_key_down("right"):
            self.yaw -= math.radians(TURN_SPEED * dt)
        fx, fz = math.sin(self.yaw), math.cos(self.yaw)
        if self.game.input.is_key_down("up"):
            self.player.move(fx * SPEED * dt, 0.0, fz * SPEED * dt)
        if self.game.input.is_key_down("down"):
            self.player.move(-fx * SPEED * dt, 0.0, -fz * SPEED * dt)

        # Clamp to the arena and place on the ground.
        px, py, pz = self.player.position
        px = max(-BOUNDS, min(BOUNDS, px))
        pz = max(-BOUNDS, min(BOUNDS, pz))
        if self.game.input.is_key_pressed("space"):
            self.hop = max(self.hop, 1.0)
        py = 1.0 + 0.9 * abs(math.sin(self.hop * math.pi)) if self.hop > 0 else 1.0
        self.hop = max(0.0, self.hop - 2.2 * dt / 0.5)
        self.player.position = (px, py, pz)
        self.player.rotation_euler = (0.0, math.degrees(self.yaw), 0.0)

        # Gems bob, rotate and get collected by walking into them.
        kept = []
        for index, gem in enumerate(self.gems):
            gem.rotation_euler = (self.elapsed * 90, self.elapsed * 60, 0.0)
            gy = 1.2 + 0.6 * math.sin(self.elapsed * 2.0 + index)
            gem.position = (gem.position.x, gy, gem.position.z)
            dx, _, dz = (gem.position.x - px), (gem.position.y - py), (gem.position.z - pz)
            if (dx * dx + dz * dz) < 1.8:
                gem.visible = False
                print("[walker] gem collected")
            else:
                kept.append(gem)
        self.gems = kept
        self.gems_left = len(self.gems)

        # Third-person camera behind the player, looking ahead along yaw.
        cam_x = px - fx * 8.5
        cam_z = pz - fz * 8.5
        self.camera.position = (cam_x, 4.4, cam_z)
        self.camera.look_at((px + fx * 4.0, 1.0, pz + fz * 4.0))

        self.hud.text = (
            f"gems {self.gems_left}   walker ({px:.1f}, {py:.1f}, {pz:.1f})"
            f"   fps {self.game.clock.fps:.0f}"
        )

        if self.game.input.is_key_pressed("r"):
            self.reset()
        if self.game.input.is_key_pressed("escape"):
            self.game.close()

    def draw(self, renderer) -> None:
        # 3D nodes through the scene camera (light drives the shading).
        renderer.begin_3d(self.camera3d, self.light)
        for x in range(-20, 21, 4):
            renderer.draw_line_3d((x, 0.0, -BOUNDS), (x, 0.0, BOUNDS), color=(34, 40, 62))
            renderer.draw_line_3d((-BOUNDS, 0.0, x), (BOUNDS, 0.0, x), color=(34, 40, 62))
        for node in self.nodes:
            node.draw(renderer)
        renderer.end_3d()

        # Screen-space HUD (Text -> renderer.draw_text).
        renderer.draw_text(self.hud)
        renderer.draw_text(self.hint)


def make_game() -> pydex_ge.Game:
    return WalkerGame()


def main() -> None:
    print("PYDEX Object 3D Walker - turn, walk, hop and collect the gems.")
    make_game().run()
    print("WalkerGame closed cleanly.")


if __name__ == "__main__":
    main()