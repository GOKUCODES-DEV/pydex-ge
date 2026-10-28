"""PYDEX field-test runner: open each game in a real SDL2 window, render
``FRAMES`` frames, then close cleanly.  Reports PASS/FAIL per game and
exits non-zero if anything crashes.

Run with:  python games/_smoke.py
"""

from __future__ import annotations

import sys
import traceback

import coin_chase
import dino_run
import dungeon_dash
import fx_arena
import mario_clone
import pacman
import pong
import shape_clicker
import snake

FRAMES = 300


def run_one(name: str, build) -> None:
    print(f"--- {name} ---")
    game = build()
    try:
        game.run(max_frames=FRAMES)
    except Exception:
        print(f"FAIL {name}: exception during run()")
        traceback.print_exc()
        return False
    print(f"PASS {name}: ran {FRAMES} frames and closed cleanly.")
    return True


def main() -> None:
    games = [
        ("Snake (2D sprites/input/labels)", snake.make_game),
        ("Pong (2D draw primitives/AI)", pong.make_game),
        ("Coin Chase (scenes/physics/camera)", coin_chase.make_game),
        ("Dungeon Dash (splash/tilemap/parallax)", dungeon_dash.make_game),
        ("FX Arena (audio/animation/camera FX)", fx_arena.make_game),
        ("Shape Clicker (events/vector math/draw)", shape_clicker.make_game),
        ("Mario Clone (tilemap/physics/audio)", mario_clone.make_game),
        ("Pac-Man (grid maze/AI/frightened)", pacman.make_game),
        ("Chrome Dino (endless runner/parallax)", dino_run.make_game),
    ]
    results = [run_one(name, build) for name, build in games]
    ok = all(results)
    print("=" * 40)
    print(f"Result: {sum(results)}/{len(results)} games passed.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()