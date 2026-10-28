"""PYDEX check demo: a clean file, a broken file, and a missing asset.

Run with:  python examples/check_demo.py

This shows, with no window and no real game assets:

1. A **valid** Python file passing :func:`pydex_ge.check_file` (empty result).
2. An **intentional syntax error** reported with the exact
   ``file:line:column`` location and the message.
3. :func:`pydex_ge.check_project` scanning a folder and reporting everything.
4. A **missing asset** raising :class:`pydex_ge.MissingAssetError` whose message
   says ``Missing asset: <filename>`` and whose ``requested_by`` names the
   ``file:line`` that asked for it.
5. :func:`pydex_ge.format_error` turning each problem into one clean line.

Everything here is headless and uses the null backend.
"""

from __future__ import annotations

import os
import tempfile

import pydex_ge
from pydex_ge.backend.null import NullBackend

GOOD_SOURCE = "x = 1\ny = x + 1\nprint(x, y)\n"

# The colon is never closed, so Python reports line 1, column 12.
BROKEN_SOURCE = "def broken(:\n    pass\n"


def main() -> None:
    print("PYDEX check demo")
    print("================")

    with tempfile.TemporaryDirectory() as tmp:
        good_path = os.path.join(tmp, "good.py")
        bad_path = os.path.join(tmp, "bad.py")
        with open(good_path, "w", encoding="utf-8") as handle:
            handle.write(GOOD_SOURCE)
        with open(bad_path, "w", encoding="utf-8") as handle:
            handle.write(BROKEN_SOURCE)

        # 1. A valid file: no problems.
        print("\n[1] check_file(good.py) ->", pydex_ge.check_file(good_path))

        # 2. A syntax error with its exact file:line:column.
        results = pydex_ge.check_file(bad_path)
        print("[2] check_file(bad.py) ->")
        for result in results:
            print("    ", result)

        # 3. Scan the whole folder.
        print("\n[3] check_project(tmp) ->")
        for result in pydex_ge.check_project(tmp):
            print("    ", result)

    # 4. A missing asset, reported through the public API.
    print("\n[4] missing asset")
    assets = pydex_ge.Assets(backend=NullBackend())
    try:
        assets.image("assets/player.png")
    except pydex_ge.MissingAssetError as exc:
        print("    message:      ", exc)
        print("    requested by: ", exc.requested_by)

    # 5. format_error produces one clean line for both kinds of problem.
    print("\n[5] format_error")
    try:
        compile(BROKEN_SOURCE, "bad.py", "exec")
    except SyntaxError as exc:
        print("    ", pydex_ge.format_error(exc))
    try:
        assets.image("assets/player.png")
    except pydex_ge.MissingAssetError as exc:
        print("    ", pydex_ge.format_error(exc))


if __name__ == "__main__":
    main()
