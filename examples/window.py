"""PYDEX Part 2 example: a working SDL2 window with a clear background.

Opens a real window, clears it to a color each frame, presents the frame,
reports timing, and closes cleanly.

Run with:  python examples/window.py
"""

import pydex_ge


def main() -> None:
    game = pydex_ge.Game("PYDEX Test", 800, 600, fps=60)
    game.background = (20, 20, 25)

    print(f"PYDEX {pydex_ge.__version__} - working window example")
    print(f"Window: {game.window.width}x{game.window.height}, background: {game.background}")
    print("Opening SDL2 window and running a few frames...")

    game.run(max_frames=120)

    print(f"Ran for {game.clock.get_time():.2f}s; window closed cleanly.")
    print("PYDEX window example finished.")


if __name__ == "__main__":
    main()