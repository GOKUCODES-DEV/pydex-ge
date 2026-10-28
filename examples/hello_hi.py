"""Part 3 final visual check: a window titled "Hi".

Deliberately minimal on purpose (Pattern of Minimum Code): a dark
background plus a handful of primitives keeps human visual inspection
fast and unambiguous. The window closes itself after five seconds.
"""

import pydex_ge


class GreetingGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Hi", 640, 480, fps=60)
        self._elapsed = 0.0
        self.background = (16, 16, 21)

    def update(self, dt: float) -> None:
        self._elapsed += dt
        if self._elapsed >= 5.0:
            self.close()

    def draw(self) -> None:
        self.renderer.draw.rect(120, 150, 200, 180, color=(0, 128, 255))
        self.renderer.draw.rect(340, 150, 200, 180, color=(255, 255, 0), filled=False)
        self.renderer.draw.circle(280, 190, 70, color=(80, 220, 120))
        self.renderer.draw.line(160, 320, 500, 320, color=(255, 255, 255))
        self.renderer.draw.pixel(138, 168, color=(255, 255, 255))


def main() -> None:
    game = GreetingGame()
    print('Hello from GreetingGame; the window title is "Hi".')
    print("Closing automatically in 5 seconds...")
    game.run()
    print("GreetingGame closed cleanly.")


if __name__ == "__main__":
    main()