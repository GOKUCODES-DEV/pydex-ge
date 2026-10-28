"""PYDEX quick start - everything is already written for you.

Just run this file:
    python quickstart.py

A window opens, a square moves, and a label counts frames.  To make it
YOUR game, only edit the two spots marked <<< >>> below - the import,
class, setup(), and run() are all done for you.

Try editing:
  * setup()  -> change title/size/fps/background, add your own state.
  * update() -> game logic every frame (movement, input, collisions).
  * draw()   -> drawing every frame (rects, labels, sprites).
"""

import pydex_ge


class MyGame(pydex_ge.Game):
    def setup(self):
        # Runs once automatically.  Configure the window here.
        self.screen = "My Game", 600, 500          # title, width, height
        self.fps = 60
        self.background = (20, 22, 30)

        # ---- your game's starting state goes here ----
        self.x = 60
        self.y = 60
        self.speed = 200                            # pixels per second
        self.frames = 0
        self.label = pydex_ge.Label(
            "Hello! 0",
            font=pydex_ge.Font(size=24),
            position=(10, 10),
            color=(255, 255, 255),
        )
        # <<< add any other starting values (score, body list, etc.) >>>

    def update(self, dt):
        # Runs every frame.  dt = seconds since the last frame.
        self.x += self.speed * dt
        if self.x > 500:
            self.x = 0
        self.frames += 1
        self.label.text = f"Hello! {self.frames}"

        # <<< your game logic goes here (movement, input, collisions) >>>

    def draw(self):
        # Runs every frame after update.  Draw your game here.
        self.renderer.draw.rect(
            self.x, self.y, 40, 40, color=(0, 255, 0), filled=True
        )
        self.renderer.draw_label(self.label)

        # <<< your drawing goes here >>>


if __name__ == "__main__":
    MyGame().run()          # create the game and start it
