"""PYDEX field-test: Shape Clicker (events + Vector math + draw primitives).

Exercises ``Scene.handle_event`` with ``EventType`` dispatch (key, mouse
button, mouse motion, window resize), ``Vector2`` math (``from_polar``,
``rotate``, ``distance_to``, ``dot``, ``clamp_length``, ...), ``Vector3``
projection for a small 3D pyramid, mouse hit-testing, and the low-level
``renderer.draw`` primitives (``pixel``, ``line``, ``rect``, ``circle``).
Click the moving shapes to score.

Controls
--------
* **Click** a shape — score points (triangle = 2, pyramid = 5, rest = 1)
* **P** — pause / unpause
* **ESC** — quit

Run with:  python games/shape_clicker.py
"""

from __future__ import annotations

import math

import pydex_ge
from pydex_ge.physics import Rect, Vector2, Vector3

W, H = 800, 600
CX, CY = 400, 300


def rotate_y(v: Vector3, degrees: float) -> Vector3:
    """Rotate a Vector3 around the Y (up) axis."""
    rad = math.radians(degrees)
    c, s = math.cos(rad), math.sin(rad)
    return pydex_ge.Vector3(v.x * c + v.z * s, v.y, -v.x * s + v.z * c)


def project(v: Vector3) -> tuple[float, float]:
    """Perspective-project a Vector3 onto the 2D screen."""
    p = 2.2 / (2.2 - v.z * 0.5)
    return (CX + v.x * p * 46, CY - v.y * p * 46)


def point_in_triangle(p: Vector2, a: Vector2, b: Vector2, c: Vector2) -> bool:
    """Barycentric sign test using Vector2 math."""
    def sign(p1: Vector2, p2: Vector2, p3: Vector2) -> float:
        return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)

    d1 = sign(p, a, b)
    d2 = sign(p, b, c)
    d3 = sign(p, c, a)
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_neg and has_pos)


class ShapeScene(pydex_ge.Scene):
    def __init__(self, game) -> None:
        super().__init__()
        self.game = game

        # -- shapes -------------------------------------------------------
        self.shapes = [
            {"kind": "circle", "pos": Vector2(150, 150), "vel": Vector2(90, 60),
             "radius": 34, "color": (120, 220, 255), "angle": 0.0, "spin": 0.0},
            {"kind": "rect", "pos": Vector2(620, 220), "vel": Vector2(-70, 45),
             "radius": 36, "color": (255, 170, 120), "angle": 0.0, "spin": 0.0},
            {"kind": "triangle", "pos": Vector2(320, 460), "vel": Vector2(55, -85),
             "radius": 40, "color": (170, 255, 140), "angle": 0.0, "spin": 70.0},
            {"kind": "star", "pos": Vector2(520, 480), "vel": Vector2(-60, -40),
             "radius": 42, "color": (255, 230, 120), "angle": 0.0, "spin": 45.0},
            {"kind": "spinner", "pos": Vector2(400, 300), "vel": Vector2(140, 0),
             "radius": 26, "color": (230, 150, 255), "angle": 0.0, "spin": 140.0},
        ]

        # Screen-space trail left behind the circle shape (pixel demo).
        self.trail: list[tuple[int, int]] = []

        # Small 3D pyramid drawn with projected Vector3 lines.
        size = 1.4
        self.pyramid = [
            Vector3(-size, 0.0, -size), Vector3(size, 0.0, -size),
            Vector3(size, 0.0, size), Vector3(-size, 0.0, size),
            Vector3(0.0, size * 1.6, 0.0),
        ]
        self.pyramid_base = CX
        self.pyramid_pos = Vector2(CX, CY - 40)
        self.pyramid_rot = 0.0

        # -- FX + HUD -------------------------------------------------------
        self.rings: list[dict] = []
        self.mouse_pos = (CX, CY)

        self.score_label = pydex_ge.Label(
            "Score: 0", font=pydex_ge.Font(size=18), position=(12, 12), color=(255, 220, 120)
        )
        self.hit_label = pydex_ge.Label(
            "Click a shape!", font=pydex_ge.Font(size=14), position=(12, 40),
            color=(180, 200, 220),
        )
        self.title = pydex_ge.Label(
            "PYDEX Shape Clicker", font=pydex_ge.Font(size=30),
            position=(CX - 150, 24), color=(255, 255, 255),
        )
        self.hint = pydex_ge.Label(
            "Click shapes to score   P: pause   ESC: quit",
            font=pydex_ge.Font(size=13), position=(CX - 140, H - 26), color=(120, 140, 165),
        )
        self.paused_label = pydex_ge.Label(
            "PAUSED", font=pydex_ge.Font(size=40), position=(CX - 60, CY - 30),
            color=(255, 255, 255), visible=False,
        )

        self.score = 0
        self.paused = False

    # -- events -------------------------------------------------------------

    def handle_event(self, event) -> None:
        super().handle_event(event)
        if event.type is pydex_ge.EventType.KEY_DOWN:
            key = event.data.get("key")
            if key == "escape":
                self.game.close()
            elif key == "p":
                self.paused = not self.paused
                self.paused_label.visible = self.paused
        elif event.type is pydex_ge.EventType.MOUSE_MOTION:
            self.mouse_pos = (event.data["x"], event.data["y"])
        elif event.type is pydex_ge.EventType.MOUSE_BUTTON_DOWN:
            if event.data.get("button") == "left":
                self._click(event.data["x"], event.data["y"])
        elif event.type is pydex_ge.EventType.WINDOW_RESIZED:
            width, height = event.data["width"], event.data["height"]
            self.title.position = (width // 2 - 150, 24)
            self.hint.position = (width // 2 - 140, height - 26)

    def _click(self, mx: int, my: int) -> None:
        point = Vector2(float(mx), float(my))
        # Hitting the projected pyramid is worth more.
        if self.pyramid_pos.distance(point) < 70:
            self.score += 5
            self.score_label.text = f"Score: {self.score}"
            self.hit_label.text = "Hit pyramid (+5)!"
            self.hit_label.color = (120, 255, 120)
            self.rings.append({"x": mx, "y": my, "r": 4.0})
            print(f"[clicker] hit pyramid at ({mx},{my}) +5")
            return
        for shape in self.shapes:
            if self._hits(shape, point):
                points = 2 if shape["kind"] == "triangle" else 1
                self.score += points
                self.score_label.text = f"Score: {self.score}"
                self.hit_label.text = f"Hit {shape['kind']} (+{points})!"
                self.hit_label.color = (120, 255, 120)
                self.rings.append({"x": mx, "y": my, "r": 4.0})
                print(f"[clicker] hit {shape['kind']} at ({mx},{my}) +{points}")
                return
        self.hit_label.text = "Miss!"
        self.hit_label.color = (255, 140, 140)

    def _hits(self, shape: dict, point: Vector2) -> bool:
        """Screen-space hit test for a 2D shape."""
        pos, radius = shape["pos"], shape["radius"]
        if shape["kind"] == "circle":
            return pos.distance(point) <= radius
        if shape["kind"] == "rect":
            return Rect(pos.x - radius, pos.y - radius, radius * 2, radius * 2) \
                .contains_point((point.x, point.y))
        if shape["kind"] == "triangle":
            a, b, c = self._triangle_vertices(shape)
            return point_in_triangle(point, a, b, c)
        return pos.distance(point) <= radius

    def _triangle_vertices(self, shape: dict) -> tuple[Vector2, Vector2, Vector2]:
        base = shape["angle"]
        center = shape["pos"]
        return tuple(
            center + pydex_ge.Vector2.from_polar(shape["radius"], base + off)
            for off in (0.0, 120.0, 240.0)
        )

    # -- loop ---------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.paused:
            return

        # Move shapes in the window, bouncing / wrapping.
        for shape in self.shapes:
            shape["pos"] = shape["pos"] + shape["vel"] * dt
            shape["angle"] += shape["spin"] * dt
            if shape["pos"].x < shape["radius"] or shape["pos"].x > W - shape["radius"]:
                shape["vel"] = pydex_ge.Vector2(-shape["vel"].x, shape["vel"].y)
            y = shape["pos"].y
            if y < shape["radius"] or y > H - shape["radius"]:
                shape["vel"] = pydex_ge.Vector2(shape["vel"].x, -shape["vel"].y)
        # The spinner orbits a fixed focal point (clamp_length exercise).
        focus = pydex_ge.Vector2(CX, CY)
        for shape in self.shapes:
            if shape["kind"] == "spinner":
                offset = shape["pos"] - focus
                shape["pos"] = focus + offset.clamp_length(110)

        # Circle leaves a fading pixel trail.
        circle = self.shapes[0]
        self.trail.append((int(circle["pos"].x), int(circle["pos"].y)))
        if len(self.trail) > 18:
            self.trail.pop(0)

        # Rotate the projected pyramid.
        self.pyramid_rot += 40 * dt

        # Advance the click rings.
        alive = []
        for ring in self.rings:
            ring["r"] += 160 * dt
            if ring["r"] < 46:
                alive.append(ring)
        self.rings = alive

    def draw(self, renderer) -> None:
        # Fading pixel trail behind the circle.
        for index, (x, y) in enumerate(self.trail):
            alpha = int(60 + index * 10)
            renderer.draw.pixel(x, y, color=(120, 220, 255, alpha))

        # The moving shapes.
        for shape in self.shapes:
            pos = shape["pos"]
            color = shape["color"]
            if shape["kind"] == "circle":
                renderer.draw.circle(int(pos.x), int(pos.y), shape["radius"], color=color)
                renderer.draw.circle(int(pos.x), int(pos.y), shape["radius"],
                                     color=(255, 255, 255), filled=False)
            elif shape["kind"] == "rect":
                renderer.draw.rect(int(pos.x - shape["radius"]), int(pos.y - shape["radius"]),
                                   shape["radius"] * 2, shape["radius"] * 2, color=color)
                renderer.draw.rect(int(pos.x - shape["radius"]), int(pos.y - shape["radius"]),
                                   shape["radius"] * 2, shape["radius"] * 2,
                                   color=(255, 255, 255), filled=False)
            elif shape["kind"] == "triangle":
                a, b, c = self._triangle_vertices(shape)
                for p1, p2 in ((a, b), (b, c), (c, a)):
                    renderer.draw.line(int(p1.x), int(p1.y), int(p2.x), int(p2.y),
                                       color=color)
            elif shape["kind"] == "star":
                outer = [pos + pydex_ge.Vector2.from_polar(shape["radius"], shape["angle"] + k * 72)
                         for k in range(5)]
                inner = [pos + pydex_ge.Vector2.from_polar(shape["radius"] * 0.45,
                                                        shape["angle"] + 36 + k * 72)
                         for k in range(5)]
                for k in range(5):
                    o1, o2 = outer[k], outer[(k + 1) % 5]
                    renderer.draw.line(int(o1.x), int(o1.y), int(inner[k].x), int(inner[k].y),
                                       color=color)
                    renderer.draw.line(int(inner[k].x), int(inner[k].y), int(o2.x), int(o2.y),
                                       color=color)
            else:  # spinner
                heading = pydex_ge.Vector2(1, 0).rotate(shape["angle"])
                renderer.draw.circle(int(pos.x), int(pos.y), shape["radius"], color=color)
                tail = pos - heading * shape["radius"]
                renderer.draw.line(int(pos.x), int(pos.y), int(tail.x), int(tail.y),
                                   color=(255, 255, 255))

        # The projected Vector3 pyramid.
        self._draw_pyramid(renderer)

        # Click rings + cursor + HUD.
        for ring in self.rings:
            renderer.draw.circle(int(ring["x"]), int(ring["y"]), int(ring["r"]),
                                 color=(255, 255, 255), filled=False)
        mx, my = self.mouse_pos
        renderer.draw.circle(mx, my, 10, color=(255, 255, 255), filled=False)
        renderer.draw.circle(mx, my, 2, color=(255, 255, 255))

        renderer.draw_label(self.score_label)
        renderer.draw_label(self.hit_label)
        renderer.draw_label(self.title)
        renderer.draw_label(self.hint)
        renderer.draw_label(self.paused_label)

    def _draw_pyramid(self, renderer) -> None:
        # Rotate every vertex around Y, project, and draw the wireframe.
        rotated = [rotate_y(v, self.pyramid_rot) for v in self.pyramid]
        screen = []
        for v in rotated:
            x, y = project(v)
            screen.append((int(self.pyramid_pos.x + x - CX),
                           int(self.pyramid_pos.y + y - CY)))
        base = screen[:4]
        tip = screen[4]
        for k in range(4):
            renderer.draw.line(base[k][0], base[k][1],
                               base[(k + 1) % 4][0], base[(k + 1) % 4][1],
                               color=(180, 150, 255))
            renderer.draw.line(base[k][0], base[k][1], tip[0], tip[1],
                               color=(220, 190, 255))


class ShapeClickerGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Shape Clicker", W, H, fps=60)
        self.background = (22, 20, 30)
        self.scenes.push(ShapeScene(self))


def make_game() -> pydex_ge.Game:
    return ShapeClickerGame()


def main() -> None:
    print("PYDEX Shape Clicker - click the moving shapes to score.")
    make_game().run()
    print("ShapeClickerGame closed cleanly.")


if __name__ == "__main__":
    main()