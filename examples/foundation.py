"""PYDEX Part 1 foundation example.

Opens an SDL2 window, runs a handful of frames at 60 FPS, reports basic
timing, and closes cleanly.

Run with:  python examples/foundation.py
"""

import pydex_ge


def main() -> None:
    game = pydex_ge.Game("PYDEX Foundation", 800, 600, fps=60)
    print(f"PYDEX {pydex_ge.__version__} - foundation example")
    print(f"Window: {game.window.width}x{game.window.height}")
    print(f"FPS cap: {game.fps}")

    game.run(max_frames=120)

    print(f"Ran for {game.clock.get_time():.2f}s; closing window.")
    print("PYDEX foundation example finished cleanly.")


if __name__ == "__main__":
    main()