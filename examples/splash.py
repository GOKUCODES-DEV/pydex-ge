"""PYDEX Part 10 example: SplashScreen with auto-transition to a menu.

A :class:`pydex_ge.SplashScreen` opens first.  It shows a runtime-generated
logo clipped to a circle, the game name and version, PYDEX branding, a
generic ``Checking...`` / ``Loading...`` / ``Starting...`` status, and a
progress bar while several assets are silently checked and loaded through
a shared :class:`pydex_ge.Assets` cache.  After ``min_duration`` it
auto-transitions to a simple menu via ``manager.replace(...)``.

Everything is generated at runtime (no asset files needed): the logo PNG
and a coin image are written to a temporary folder.  The logo is a square
image with corner markers; the ``logo_shape="circle"`` clipping erases
those corners, so the clipping is visible on screen.

Controls: ESC closes the game (the splash is cancellable).  The example
also closes itself after ~20 seconds.

Run with:  python examples/splash.py
"""

from __future__ import annotations

import struct
import tempfile

import pydex_ge

# -- tiny runtime PNG generator (standard library only) ------------------


def _png_bytes(width: int, height: int, rows: list[bytes]) -> bytes:
    """Encode RGBA rows (top-down, ``width * 4`` bytes each) as a PNG."""
    import zlib

    def _chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    scanlines = b"".join(b"\x00" + row for row in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(scanlines))
        + _chunk(b"IEND", b"")
    )


def _solid_rows(width: int, height: int, color) -> list[bytes]:
    row = bytes((*color, 255)) * width
    return [row] * height


def _logo_rows(size: int) -> list[bytes]:
    """A square logo: indigo background, gold disc, white corner dots.

    The white corner dots sit outside the inscribed circle, so the
    ``logo_shape="circle"`` clipping visibly removes them.
    """
    bg = (24, 34, 60)
    gold = (255, 200, 60)
    white = (245, 245, 250)
    rows = []
    center = size // 2
    radius = size // 3
    for y in range(size):
        line = bytearray()
        for x in range(size):
            if (x - center) ** 2 + (y - center) ** 2 <= radius ** 2:
                line += bytes((*gold, 255))
            elif (x <= 5 and y <= 5) or (x >= size - 6 and y <= 5) or (
                x <= 5 and y >= size - 6
            ) or (x >= size - 6 and y >= size - 6):
                line += bytes((*white, 255))
            else:
                line += bytes((*bg, 255))
        rows.append(bytes(line))
    return rows


# -- scenes --------------------------------------------------------------


class MainMenu(pydex_ge.Scene):
    """The scene the splash auto-transitions into once it is done."""

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        font = pydex_ge.Font(size=28)
        small = pydex_ge.Font(size=16)
        self.add(
            pydex_ge.Label(
                "Welcome! Splash complete.",
                font=font,
                position=(235, 270),
                color=(255, 255, 255),
            )
        )
        self.add(
            pydex_ge.Label(
                "ESC quits.  The demo also closes itself after 20s.",
                font=small,
                position=(225, 330),
                color=(160, 175, 195),
            )
        )

    def on_enter(self) -> None:
        print("[menu] entered — the splash transitioned to the menu.")

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.game.input.is_key_pressed("escape"):
            self.game.close()


# -- application ---------------------------------------------------------


class SplashDemo(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Splash Screen", 800, 600, fps=60)
        self.background = (14, 18, 28)
        self._elapsed = 0.0

        self.assets = pydex_ge.Assets()
        self._tmp = tempfile.TemporaryDirectory()

        self.logo_path = f"{self._tmp.name}/logo.png"
        with open(self.logo_path, "wb") as handle:
            handle.write(_png_bytes(192, 192, _logo_rows(192)))

        self.coin_path = f"{self._tmp.name}/coin.png"
        with open(self.coin_path, "wb") as handle:
            handle.write(_png_bytes(16, 16, _solid_rows(16, 16, (255, 210, 60))))

        self.scenes.push(
            pydex_ge.SplashScreen(
                logo=self.logo_path,
                logo_shape="circle",
                name="Splash Demo",
                name_color=(235, 240, 250),
                version="1.0.0",
                loading_speed=2.0,
                file_checking=True,
                loadables=[
                    ("image", self.coin_path),
                    ("sprite_sheet", self.coin_path, 8, 8),
                    lambda assets: None,
                ],
                assets=self.assets,
                next_scene=lambda: MainMenu(self),
                game=self,
                background_color=(14, 18, 28),
                loading_color=(255, 210, 60),
                min_duration=3.0,
                cancellable=True,
            )
        )

    def update(self, dt: float) -> None:
        self._elapsed += dt
        if self._elapsed > 20.0:
            print("Demo complete - closing window.")
            self.close()

    def close(self) -> None:
        self.assets.clear()
        super().close()


def main() -> None:
    print(
        "PYDEX splash-screen example.\n"
        "The splash checks files, loads assets, then auto-transitions to a menu. "
        "ESC quits."
    )
    game = SplashDemo()
    game.run()
    print("SplashDemo closed cleanly.")


if __name__ == "__main__":
    main()
