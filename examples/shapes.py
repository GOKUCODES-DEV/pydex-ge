"""PYDEX Part 3 example: 2D rendering primitives.

Draws rectangles (filled and outlined), circles (filled and outlined), a
line, and pixels onto a real SDL2 window.

Run with:  python examples/shapes.py
Close the window (X button) when you are done inspecting the shapes.
"""

import pydex_ge


class ShapesGame(pydex_ge.Game):
    def draw(self) -> None:
        # The frame is already cleared to self.background by the game loop.
        self.renderer.draw.rect(50, 50, 200, 120, color=(255, 0, 0))
        self.renderer.draw.rect(300, 50, 200, 120, color=(255, 255, 0), filled=False)
        self.renderer.draw.circle(180, 340, 60, color=(0, 255, 0))
        self.renderer.draw.circle(460, 340, 60, color=(0, 150, 255), filled=False)
        self.renderer.draw.line(80, 470, 560, 470, color=(255, 255, 255))
        for offset in range(40):
            self.renderer.draw.pixel(100 + offset, 220, color=(255, 128, 0))


def main() -> None:
    game = ShapesGame("PYDEX Shapes", 640, 480, fps=60)
    game.background = (20, 20, 25)
    print("PYDEX shapes example - close the window to exit.")
    game.run()


if __name__ == "__main__":
    main()