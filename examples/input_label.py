"""PYDEX Part 5 example: input, text, and labels.

Opens a real SDL2 window that shows "Press E".  Pressing **E** changes the
label to "E was pressed!" and turns it green so the change is obvious.
Press **ESC** or close the window to quit.

Run with:  python examples/input_label.py
"""

import pydex_ge


class InputLabelGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Input + Label", 640, 480, fps=60)
        self.background = (18, 18, 24)

        # Explicit custom font path is loaded straight from the project
        # (here we fall back to a system font if arial.ttf is not present).
        font = pydex_ge.Font(size=32)
        self.prompt = pydex_ge.Label("Press E", font=font, position=(180, 200))
        self.hint = pydex_ge.Label(
            "E: activate   ESC: quit",
            font=pydex_ge.Font(size=16),
            position=(180, 260),
            color=(120, 130, 150),
        )
        self._activated = False

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("e") and not self._activated:
            self._activated = True
            self.prompt.text = "E was pressed!"
            self.prompt.color = (120, 255, 120)
        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        self.renderer.draw_label(self.prompt)
        self.renderer.draw_label(self.hint)


def main() -> None:
    game = InputLabelGame()
    print("PYDEX input + label example - press E, or ESC to quit.")
    game.run()
    print("InputLabelGame closed cleanly.")


if __name__ == "__main__":
    main()
