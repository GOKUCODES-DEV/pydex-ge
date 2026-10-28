"""PYDEX field-test: Coin Chase (scenes + physics + camera follow).

Exercises the scene stack (``SceneManager``: menu -> game -> game over),
the 2D ``Camera2D`` follow camera with world bounds, the physics
``World``/``Body`` (gravity, jump, static rectangles), procedural
``Sprite.from_pixels`` art, and ``Label`` HUD.  Hop across the platforms,
collect all coins, and do not fall into the void.

Controls
--------
* **Left / Right** — run
* **Space** — jump (only on the ground)
* **ESC** — quit

Run with:  python games/coin_chase.py
"""

from __future__ import annotations

import pydex_ge
from pydex_ge.physics import Rect

W, H = 800, 600
WORLD_W, WORLD_H = 1600, 1000
GRAVITY = (0, 520.0)
MOVE_SPEED = 300.0
JUMP_VELOCITY = -480.0
PLAYER_W, PLAYER_H = 28, 36
CELL = 16


def solid_pixels(width: int, height: int, color) -> bytes:
    """A width*height solid RGBA pixel block (no asset files needed)."""
    row = bytes((*color, 255)) * width
    return row * height


class MenuScene(pydex_ge.Scene):
    """Title screen; SPACE starts the game."""

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.add(pydex_ge.Label(
            "PYDEX Coin Chase", font=pydex_ge.Font(size=40), position=(280, 180), color=(255, 255, 255)
        ))
        self.add(pydex_ge.Label(
            "Hop the platforms and grab every coin!",
            font=pydex_ge.Font(size=18), position=(250, 250), color=(180, 200, 220),
        ))
        self.add(pydex_ge.Label(
            "SPACE: start   ESC: quit",
            font=pydex_ge.Font(size=16), position=(310, 320), color=(255, 210, 90),
        ))

    def on_enter(self) -> None:
        print("[menu] entered")

    def on_exit(self) -> None:
        print("[menu] exited (suspended above)")

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.game.input.is_key_pressed("space"):
            self.manager.push(GameScene(self.game))
        elif self.game.input.is_key_pressed("escape"):
            self.game.close()


class GameScene(pydex_ge.Scene):
    """Platforming that tests Camera2D follow and physics."""

    def __init__(self, game) -> None:
        super().__init__(camera=pydex_ge.Camera2D(W, H, position=(W // 2, H // 2)))
        self.game = game

        # -- world -----------------------------------------------------
        # Platform steps stay within the max jump height (~221 px: gravity
        # 520, jump 480) so every platform is reachable.
        self.floor = Rect(0, WORLD_H - 60, WORLD_W, 60)
        self.platforms = (
            Rect(700, 850, 270, 22),
            Rect(1120, 720, 270, 22),
            Rect(360, 560, 210, 22),
        )
        self.world = pydex_ge.World(gravity=GRAVITY, static_rects=(self.floor,) + self.platforms)
        self.body = pydex_ge.Body(
            position=(200, WORLD_H - 60 - PLAYER_H),
            size=(PLAYER_W, PLAYER_H),
            velocity=(0, 0),
        )
        self.world.add_body(self.body)

        # -- sprites ----------------------------------------------------
        self.player = pydex_ge.Sprite.from_pixels(
            PLAYER_W, PLAYER_H, solid_pixels(PLAYER_W, PLAYER_H, (120, 210, 255))
        )
        self.player.z = 2

        self.floor_sprite = pydex_ge.Sprite.from_pixels(
            WORLD_W, 60, solid_pixels(WORLD_W, 60, (40, 90, 60))
        )
        self.floor_sprite.position = (0, WORLD_H - 60)
        self.platform_sprites = [
            pydex_ge.Sprite.from_pixels(int(rect.width), int(rect.height),
                                     solid_pixels(int(rect.width), int(rect.height), (70, 90, 120)))
            for rect in self.platforms
        ]
        for sprite, rect in zip(self.platform_sprites, self.platforms):
            sprite.position = (int(rect.x), int(rect.y))

        # Coins sit just above each surface so they are easy to grab.
        self.coins = [
            pydex_ge.Sprite.from_pixels(CELL, CELL, solid_pixels(CELL, CELL, (255, 205, 60)))
            for _ in range(6)
        ]
        for sprite, (x, y) in zip(self.coins, (
                (250, 905), (520, 905), (770, 815),
                (1240, 685), (430, 525), (1380, 905))):
            sprite.position = (x, y)
            sprite.z = 1

        # -- camera & HUD -----------------------------------------------
        self.camera.bounds = Rect(0, 0, WORLD_W, WORLD_H)
        self.camera.follow(self.body, smoothing=5.0)

        self.coins_label = pydex_ge.Label(
            f"Coins: {len(self.coins)}", font=pydex_ge.Font(size=16), position=(12, 12), color=(255, 220, 120)
        )
        self.hint_label = pydex_ge.Label(
            "Arrows: move   Space: jump   ESC: quit",
            font=pydex_ge.Font(size=14), position=(12, 36), color=(150, 160, 185),
        )

        for obj in (self.floor_sprite, *self.platform_sprites, self.player, *self.coins,
                    self.coins_label, self.hint_label):
            self.add(obj)

    def on_enter(self) -> None:
        print("[game] entered")

    def on_exit(self) -> None:
        print("[game] exited")

    def update(self, dt: float) -> None:
        dx = 0.0
        if self.game.input.is_key_down("left"):
            dx -= MOVE_SPEED
        if self.game.input.is_key_down("right"):
            dx += MOVE_SPEED
        self.body.velocity = (dx, self.body.velocity.y)

        grounded = (
            any(self.body.collides_with(rect) for rect in (self.floor,) + self.platforms)
            and self.body.velocity.y == 0
        )
        if self.game.input.is_key_pressed("space") and grounded:
            self.body.apply_impulse((0, JUMP_VELOCITY))

        self.world.update(dt)
        self.body.position = (max(0.0, min(self.body.position.x, WORLD_W - PLAYER_W)), self.body.position.y)
        self.camera.update(dt)
        self.player.position = (int(self.body.position.x), int(self.body.position.y))

        if self.game.input.is_key_pressed("escape"):
            self.manager.pop()
            return

        for coin in list(self.coins):
            if self.body.rect.overlaps(Rect(int(coin.x), int(coin.y), int(coin.width), int(coin.height))):
                self.coins.remove(coin)
                self.remove(coin)
                print(f"[game] coin collected ({len(self.coins)} left)")
        self.coins_label.text = f"Coins: {len(self.coins)}"

        if self.body.position.y > WORLD_H + 80:
            self.manager.replace(GameOverScene(self.game, "You fell off the world!"))
        elif not self.coins:
            self.manager.replace(GameOverScene(self.game, "All coins collected - you win!"))


class GameOverScene(pydex_ge.Scene):
    """Result screen; SPACE/ENTER returns to the menu."""

    def __init__(self, game, message: str) -> None:
        super().__init__()
        self.game = game
        self.add(pydex_ge.Label(message, font=pydex_ge.Font(size=22), position=(W // 2 - 190, H // 2 - 30),
                             color=(255, 210, 90)))
        self.add(pydex_ge.Label("ENTER: menu   ESC: quit", font=pydex_ge.Font(size=15),
                             position=(W // 2 - 110, H // 2 + 30), color=(150, 160, 185)))

    def on_enter(self) -> None:
        print("[gameover] entered")

    def on_exit(self) -> None:
        print("[gameover] exited")

    def update(self, dt: float) -> None:
        if self.game.input.is_key_pressed("space") or self.game.input.is_key_pressed("return"):
            self.manager.pop()
        elif self.game.input.is_key_pressed("escape"):
            self.game.close()


class CoinChaseGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Coin Chase", W, H, fps=60)
        self.background = (14, 18, 28)
        self.scenes.push(MenuScene(self))


def make_game() -> pydex_ge.Game:
    return CoinChaseGame()


def main() -> None:
    print("PYDEX Coin Chase - scenes, physics, and a follow camera.")
    make_game().run()
    print("CoinChaseGame closed cleanly.")


if __name__ == "__main__":
    main()