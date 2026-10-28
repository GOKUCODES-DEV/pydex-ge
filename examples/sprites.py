"""PYDEX Part 4 example: images, textures, and sprites.

Demonstrates the three sprite sources in one real SDL2 window:

* an image-file sprite (``player.png``, with transparency),
* a pixel-created sprite (``Sprite.from_pixels``), and
* sprite-sheet / texture-region sprites cut from ``tiles.bmp``.

Sprites are drawn scaled and (for one) semi-transparent.  The window
closes on its own after a few seconds.

Run with:  python examples/sprites.py
"""

import os

import pydex_ge

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
PLAYER_PNG = os.path.join(ASSET_DIR, "player.png")
TILES_BMP = os.path.join(ASSET_DIR, "tiles.bmp")


def pixel_face() -> bytes:
    """A 16x16 RGBA pixel sprite: a checker-shaded round face."""
    size = 16
    pixels = bytearray(size * size * 4)
    center_x, center_y, radius = 7.5, 7.5, 6.0
    for index in range(size * size):
        x, y = index % size, index // size
        inside = (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2
        if inside:
            if (x // 2 + y // 2) % 2 == 0:
                color = (255, 220, 60, 255)
            else:
                color = (255, 170, 30, 255)
        else:
            color = (0, 0, 0, 0)
        start = index * 4
        pixels[start:start + 4] = bytes(color)
    return bytes(pixels)


class SpritesGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Sprites", 640, 480, fps=60)
        self._elapsed = 0.0
        self.background = (18, 18, 24)
        self.assets = pydex_ge.Assets()

        self.player = pydex_ge.Sprite(self.assets.image(PLAYER_PNG))
        self.player.position = (120, 90)
        self.player.scale = 2.0

        self.pixel = pydex_ge.Sprite.from_pixels(16, 16, pixel_face())
        self.pixel.position = (300, 80)
        self.pixel.scale = 3.0

        sheet = pydex_ge.SpriteSheet(self.assets.image(TILES_BMP), 32, 32)
        self.floor = sheet.sprite(0, 0, 32, 32)
        self.floor.position = (120, 320)
        self.floor.scale = 3.0
        self.floor_alt = sheet.sprite(32, 0, 32, 32)
        self.floor_alt.position = (280, 330)
        self.floor_alt.alpha = 150

    def update(self, dt: float) -> None:
        self._elapsed += dt
        if self._elapsed >= 6.0:
            self.close()

    def draw(self) -> None:
        self.renderer.draw_sprite(self.player)
        self.renderer.draw_sprite(self.pixel)
        self.renderer.draw_sprite(self.floor)
        self.renderer.draw_sprite(self.floor_alt)


def main() -> None:
    game = SpritesGame()
    print("PYDEX sprites example - image, pixel, and sheet sprites.")
    print("Closing automatically in 6 seconds...")
    game.run()
    print("SpritesGame closed cleanly.")


if __name__ == "__main__":
    main()