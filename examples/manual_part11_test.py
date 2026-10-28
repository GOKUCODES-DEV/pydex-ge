"""Temporary manual test for Part 11: Error and Syntax Checking.

Demonstrates the headless error/syntax-checking system added in Part 11:

* **Valid file**          ``check_file()`` on a correct ``.py`` returns ``[]``.
* **Syntax error**        ``check_file()`` reports the exact ``path:line:column``
                          for an intentional ``def broken(:`` error.
* **Project-wide check**  ``check_project()`` scans a whole folder and finds
                          every broken ``.py`` file inside it.
* **Missing asset**       asking for a file that does not exist raises
                          ``MissingAssetError`` whose message says
                          ``Missing asset: <filename>`` and whose
                          ``requested_by`` names the caller's ``file:line``.
* **format_error**        turns either problem into one clean
                          ``file:line: ErrorType: message`` line, pointing at
                          the caller (this file), not PYDEX internals.

Run modes::

    python examples/manual_part11_test.py --check     # headless assertions
    python examples/manual_part11_test.py --demo      # guided run, no pauses
    python examples/manual_part11_test.py             # guided run, press Enter
    python examples/manual_part11_test.py --gui       # windowed splash + on-screen errors

The ``--gui`` mode opens an 800x600 PYDEX window that mimics a splash
screen: it shows a generic ``Checking...`` status for a moment, runs
``check_project()`` on a generated project that contains one intentional
syntax error, and then renders the reported problem(s) directly on the
screen in red (or a green ``All files valid.`` when everything passes).
``format_error`` lines are shown underneath.  ESC closes the window; it
also closes itself after ~15 seconds.

The guided run is headless too (no window is opened); it just walks the
checks one at a time so each message can be read.  Everything is written
into a temporary folder, so nothing is created or changed in this repo.

This file is a manual verification aid only; it is not part of the public
PYDEX API and may be deleted at any time.
"""

from __future__ import annotations

import os
import sys
import tempfile

import pydex_ge
from pydex_ge.backend.null import NullBackend

GOOD_SOURCE = (
    '"""A perfectly valid module."""\n'
    "import math\n"
    "\n"
    "\n"
    "def double(x: float) -> float:\n"
    "    return x * 2\n"
    "\n"
    "\n"
    "VALUE = double(math.pi)\n"
)

# Line 2 holds the error on purpose: ``(`` is column 11 and ``:`` is
# column 12 (1-based), so the report should read ``bad.py:2:12``.
BROKEN_SOURCE = (
    '"""A module with one intentional syntax error."""\n'
    "def broken(:  \n"
    "    pass\n"
)

SECOND_BROKEN_SOURCE = (
    '"""Another broken module, in a subfolder."""\n'
    "x = [1, 2\n"
)


def _banner(title: str, rule: str = "=") -> None:
    print(f"\n{rule * 60}")
    print(title)
    print(rule * 60)


# -- guided walkthrough (interactive by default) --------------------------


def _step(pause: bool, title: str) -> None:
    _banner(title, "-")
    if pause:
        try:
            input("  [press Enter to continue] ")
        except EOFError:
            pass


def demo(pause: bool = True) -> None:
    """Run every Part 11 check one section at a time."""
    print("PYDEX Part 11 manual test (guided walkthrough).")
    print("Everything is written to a temporary folder; the repo is untouched.")

    with tempfile.TemporaryDirectory() as tmp:
        # 1. A valid Python file -------------------------------------------------
        _step(pause, "[1] Valid file - check_file()")
        good = os.path.join(tmp, "good.py")
        with open(good, "w", encoding="utf-8") as handle:
            handle.write(GOOD_SOURCE)

        results = pydex_ge.check_file(good)
        print(f"    checked : {good}")
        print(f"    problems: {results}")
        print(f"    -> {'valid (no problems reported)' if not results else 'FAIL'}")

        # 2. An intentional syntax error with exact line and column --------------
        _step(pause, "[2] Syntax error - check_file() reports line and column")
        bad = os.path.join(tmp, "bad.py")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write(BROKEN_SOURCE)

        results = pydex_ge.check_file(bad)
        for problem in results:
            print(f"    {problem}")
        print("    -> expected 'bad.py:2:12: invalid syntax' (line 2, column 12)")

        # 3. A project-wide check ------------------------------------------------
        _step(pause, "[3] Project-wide check - check_project()")
        project = os.path.join(tmp, "my_game")
        os.makedirs(os.path.join(project, "scenes"))
        for rel in ("main.py", "scenes/level.py", "scenes/ui.py"):
            with open(os.path.join(project, rel), "w", encoding="utf-8") as handle:
                handle.write(GOOD_SOURCE.replace("double", "double_" + rel.replace("/", "_").replace(".py", "")))
        second_bad = os.path.join(project, "scenes", "ui.py")
        with open(second_bad, "w", encoding="utf-8") as handle:
            handle.write(SECOND_BROKEN_SOURCE)

        results = pydex_ge.check_project(project)
        print(f"    scanned: {project}  (good.py, main.py, scenes/level.py, scenes/ui.py)")
        print(f"    problems ({len(results)}):")
        for problem in results:
            print(f"      {problem}")
        print("    -> only broken files are reported; valid ones are silent")

        # 4. A missing asset -----------------------------------------------------
        _step(pause, "[4] Missing asset - Missing asset: <name>")
        assets = pydex_ge.Assets(backend=NullBackend())
        try:
            assets.image(os.path.join(tmp, "player.png"))
            print("    -> FAIL: expected MissingAssetError")
        except pydex_ge.MissingAssetError as exc:
            print(f"    type         : {type(exc).__name__}")
            print(f"    message      : {exc}")
            print(f"    starts with  : {str(exc).startswith('Missing asset: player.png')}")
            print(f"    requested_by : {exc.requested_by}")
            print(f"    points at us : {os.path.basename(exc.requested_by or '?').startswith('manual_part11_test')}")

        # 5. format_error() shows the caller's file and line ---------------------
        _step(pause, "[5] format_error - one clean line, caller's file and line")
        print("    SyntaxError:")
        try:
            compile(BROKEN_SOURCE, os.path.join(tmp, "bad.py"), "exec")
        except SyntaxError as exc:
            print(f"      {pydex_ge.format_error(exc)}")

        print("    MissingAssetError (uses requested_by):")
        try:
            assets.image(os.path.join(tmp, "player.png"))
        except pydex_ge.MissingAssetError as exc:
            print(f"      {pydex_ge.format_error(exc)}")

        print("    ConfigurationError (uses caller frame):")
        try:
            pydex_ge.SceneManager().push("not a scene")
        except pydex_ge.ConfigurationError as exc:
            print(f"      {pydex_ge.format_error(exc)}")
        print(f"    -> every line names {os.path.basename(__file__)}")

    print("\nAll five sections completed.  Now run the headless assertions:")
    print("  python examples/manual_part11_test.py --check")


# -- headless assertions ----------------------------------------------------


def run_checks() -> None:
    ok = 0

    with tempfile.TemporaryDirectory() as tmp:
        good = os.path.join(tmp, "good.py")
        with open(good, "w", encoding="utf-8") as handle:
            handle.write(GOOD_SOURCE)
        results = pydex_ge.check_file(good)
        assert results == [], f"valid file should be silent, got {results}"
        ok += 1

        bad = os.path.join(tmp, "bad.py")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write(BROKEN_SOURCE)
        results = pydex_ge.check_file(bad)
        assert len(results) == 1, f"expected one problem, got {results}"
        problem = results[0]
        assert problem.path == os.path.abspath(bad)
        assert problem.lineno == 2, f"expected line 2, got {problem.lineno}"
        assert problem.column == 12, f"expected column 12, got {problem.column}"
        assert "invalid syntax" in problem.message, f"unexpected message {problem.message!r}"
        assert "bad.py:2:12" in str(problem), f"bad str rendering {problem}"
        ok += 1

        project = os.path.join(tmp, "my_game")
        os.makedirs(os.path.join(project, "scenes"))
        with open(os.path.join(project, "main.py"), "w", encoding="utf-8") as handle:
            handle.write(GOOD_SOURCE)
        with open(os.path.join(project, "scenes", "level.py"), "w", encoding="utf-8") as handle:
            handle.write(GOOD_SOURCE)
        second_bad = os.path.join(project, "scenes", "ui.py")
        with open(second_bad, "w", encoding="utf-8") as handle:
            handle.write(SECOND_BROKEN_SOURCE)

        results = pydex_ge.check_project(project)
        assert len(results) == 1, f"project scan should find exactly one problem, got {results}"
        assert results[0].path == os.path.abspath(second_bad)
        assert results[0].lineno == 2 and results[0].column == 5
        ok += 1

        assets = pydex_ge.Assets(backend=NullBackend())
        missing = os.path.join(tmp, "player.png")
        try:
            assets.image(missing)
            raise AssertionError("missing asset should have raised")
        except pydex_ge.MissingAssetError as exc:
            assert isinstance(exc, pydex_ge.BackendError), "MissingAssetError must be a BackendError"
            assert str(exc).startswith("Missing asset: player.png"), f"bad message {exc}"
            assert "looked for" in str(exc), f"message should include the full path, got {exc}"
            assert exc.requested_by is not None, "requested_by must be set"
            assert os.path.basename(exc.requested_by).startswith("manual_part11_test"), (
                f"requested_by should point into this file, got {exc.requested_by}"
            )
        ok += 1

        try:
            compile(BROKEN_SOURCE, os.path.join(tmp, "bad.py"), "exec")
        except SyntaxError as exc:
            line = pydex_ge.format_error(exc)
            assert line.endswith("bad.py:2:12: SyntaxError: invalid syntax"), f"bad line {line}"
            ok += 1

        try:
            assets.image(missing)
        except pydex_ge.MissingAssetError as exc:
            line = pydex_ge.format_error(exc)
            assert line.startswith(exc.requested_by), f"format_error should use requested_by, got {line}"
            assert ": MissingAssetError: Missing asset: player.png" in line, f"bad line {line}"
            ok += 1

        try:
            pydex_ge.SceneManager().push("not a scene")
        except pydex_ge.ConfigurationError as exc:
            line = pydex_ge.format_error(exc)
            assert "manual_part11_test.py:" in line, (
                f"format_error should name this file, got {line}"
            )
            assert ": ConfigurationError: " in line, f"bad line {line}"
            ok += 1

    print(f"All {ok} Part 11 checks passed.")


# -- windowed splash with on-screen errors ---------------------------------


def _syntax_token(result) -> str:
    """The offending code at the error column, read from the source file.

    ``x = [1, 2`` (line 2, column 5) becomes ``[``; ``def broken(:``
    (column 12) becomes ``:``.  Falls back to the message when the file
    cannot be read.
    """
    if result.column and result.path:
        try:
            with open(result.path, "r", encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
            if 1 <= result.lineno <= len(lines):
                line = lines[result.lineno - 1]
                if 0 < result.column <= len(line):
                    return line[result.column - 1]
        except OSError:
            pass
    return result.message or "?"


def _short_error(item) -> str:
    """One short on-screen line, no full paths.

    A syntax problem becomes ``err:syntax:<line> > <code>`` (for example
    ``err:syntax:2 > [``); a missing asset becomes
    ``err:missing:asset/<name> : called at line <line>``.
    """
    if isinstance(item, pydex_ge.MissingAssetError):
        name = os.path.basename(item.path) if item.path else "?"
        line = ""
        if item.requested_by and ":" in item.requested_by:
            line = item.requested_by.rsplit(":", 1)[-1]
        return f"err:missing:asset/{name} : called at line {line}"
    lineno = getattr(item, "lineno", None)
    code = _syntax_token(item)
    return f"err:syntax:{lineno} > {code}"


class CheckSplashScene(pydex_ge.Scene):
    """A splash-like scene that checks a project, then shows the problems.

    Phase ``checking`` shows a small ``Checking...`` for a moment; phase
    ``results`` replaces that very line with the error itself, in small red
    text, one short ``err: <type>: <line>`` per problem (no full paths).
    When everything passes it shows a small green ``All files valid.``
    """

    W, H = 800, 600

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self._phase = "checking"
        self._timer = 0.0
        self._results: list = []

        self._title = pydex_ge.Label(
            "PYDEX Part 11 - checking your project",
            font=pydex_ge.Font(size=20),
            position=(0, 50),
            color=(235, 240, 250),
        )
        self._status = pydex_ge.Label(
            "Checking...",
            font=pydex_ge.Font(size=15),
            position=(0, 130),
            color=(255, 210, 60),
        )
        self._hint = pydex_ge.Label(
            "ESC closes the window (it also closes itself after ~15s).",
            font=pydex_ge.Font(size=12),
            position=(0, 560),
            color=(150, 155, 165),
        )
        self._rows = [
            pydex_ge.Label(
                "",
                font=pydex_ge.Font(size=13),
                position=(0, 170 + i * 22),
                color=(255, 90, 90),
            )
            for i in range(8)
        ]
        for label in (self._title, self._status, self._hint):
            label.x = (self.W - label.width) // 2

    def update(self, dt: float) -> None:
        super().update(dt)
        if self._phase == "checking":
            self._timer += dt
            if self._timer >= 0.8:
                self._phase = "results"
                self._run_check()
        if self.game.input.is_key_pressed("escape"):
            self.game.close()

    def _run_check(self) -> None:
        results = list(pydex_ge.check_project(self.game.project_dir))
        if self.game.missing_error is not None:
            results.append(self.game.missing_error)
        self._results = results
        if results:
            self._status.text = _short_error(results[0])
            self._status.color = (255, 90, 90)
            for i, label in enumerate(self._rows):
                label.text = _short_error(results[i]) if i < len(results) else ""
        else:
            self._status.text = "All files valid."
            self._status.color = (140, 220, 150)
        self._status.x = (self.W - self._status.width) // 2

    def draw(self, renderer) -> None:
        renderer.clear((14, 18, 28))
        for label in (self._title, self._status, *self._rows, self._hint):
            renderer.draw_label(label)


class Part11CheckDemo(pydex_ge.Game):
    """Windowed demo: a splash screen that checks a generated project."""

    def __init__(self) -> None:
        super().__init__("PYDEX Part 11 check", 800, 600, fps=60)
        self.background = (14, 18, 28)
        self._elapsed = 0.0
        self._tmp = tempfile.TemporaryDirectory()

        project = os.path.join(self._tmp.name, "my_game")
        os.makedirs(os.path.join(project, "scenes"))
        with open(os.path.join(project, "main.py"), "w", encoding="utf-8") as handle:
            handle.write(GOOD_SOURCE)
        with open(os.path.join(project, "scenes", "level.py"), "w", encoding="utf-8") as handle:
            handle.write(GOOD_SOURCE)
        broken = os.path.join(project, "scenes", "ui.py")
        with open(broken, "w", encoding="utf-8") as handle:
            handle.write(SECOND_BROKEN_SOURCE)
        self.project_dir = project

        self.missing_error = None
        try:
            pydex_ge.Assets().image(os.path.join(self._tmp.name, "player.png"))
        except pydex_ge.MissingAssetError as exc:
            self.missing_error = exc

        self.scenes.push(CheckSplashScene(self))
        print(f"Checking generated project: {project}")
        print("The window shows the result on the splash screen.")

    def update(self, dt: float) -> None:
        self._elapsed += dt
        if self._elapsed > 15.0:
            print("Demo complete - closing window.")
            self.close()

    def close(self) -> None:
        self._tmp.cleanup()
        super().close()


# -- entry point ------------------------------------------------------------


def main():
    if "--check" in sys.argv:
        run_checks()
        return
    if "--gui" in sys.argv:
        game = Part11CheckDemo()
        game.run()
        print("Part11CheckDemo closed cleanly.")
        return
    demo(pause="--demo" not in sys.argv)


if __name__ == "__main__":
    main()
