"""Command line entry point for dexpen.

Usage::

    python -m pydex_ge.dexpen hero.png
    python -m pydex_ge.dexpen --width 64 --height 48 art.png
    python -m pydex_ge.dexpen --new existing.png
"""

from __future__ import annotations

import argparse
import os

from .canvas import Canvas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pydex_ge.dexpen",
        description="PYDEX pixel-art editor.",
    )
    parser.add_argument("path", nargs="?", default=None, help="sprite file (PNG/BMP) to open or save to")
    parser.add_argument("--width", type=int, default=32, help="new canvas width (default 32)")
    parser.add_argument("--height", type=int, default=32, help="new canvas height (default 32)")
    parser.add_argument(
        "--new", action="store_true",
        help="start a fresh canvas even if the file already exists",
    )
    args = parser.parse_args(argv)

    from . import PixelEditor

    canvas: Canvas | None = None
    if args.path and os.path.exists(args.path) and not args.new:
        try:
            canvas = Canvas.load(args.path)
        except Exception as exc:  # pragma: no cover - CLI path
            parser.error(f"could not open {args.path!r}: {exc}")
    if canvas is None:
        canvas = Canvas(args.width, args.height, color=(0, 0, 0, 0))

    game = PixelEditor(canvas, path=args.path)
    game.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())