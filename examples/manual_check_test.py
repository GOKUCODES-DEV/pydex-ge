"""MANUAL / TEMPORARY test file for the PYDEX project checker.

This file is NOT part of the PYDEX engine API.  It is a self-checking demo
that lets a developer (or the test suite) confirm the checker finds the
problems it is supposed to find.

Run with::

    python examples/manual_check_test.py --check

It creates a small temporary project packed with *intentional* mistakes and
reports every problem the checker detects:

* syntax error            (SYNTAX001)
* invalid import          (IMPORT001)
* undefined name          (NAME001)
* PYDEX typo              (PYDEX001)
* configuration problem   (CONFIG001)
* missing asset           (ASSET001)

and finishes with a valid project to show the clean path.  Nothing here is
executed by PYDEX and no window is ever opened.
"""

from __future__ import annotations

import os
import sys
import tempfile

import pydex_ge

_BROKEN_PROJECT = {
    # Syntax error: the colon is never closed.
    "broken.py": "def broken(:\n    pass\n",
    # Bad import, bad name, PYDEX typo, and a missing asset.
    "main.py": (
        "from pydex_ge import Spritee\n"
        "import pydex_ge\n"
        "camera = pydex_ge.Camra2D()\n"
        'player = pydex_ge.Sprite("player.png")\n'
        "print(total)\n"
    ),
    # Configuration problem.
    "config.py": 'game = pydex_ge.Game("x", 640, 480, fps="high")\n',
    # Valid project to prove the clean path works.
    "valid/ok.py": "import pydex_ge\nx = 1\nprint(x)\n",
}

# Codes we expect to see in the broken project.
_EXPECTED_ERROR_CODES = {"SYNTAX001", "IMPORT001", "PYDEX001", "CONFIG001", "ASSET001"}
_EXPECTED_WARNING_CODES = {"NAME001"}


def _build_project(root: str) -> None:
    for rel, text in _BROKEN_PROJECT.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


def _codes(report) -> set[str]:
    return {r.code for r in report}


def main() -> int:
    if "--check" not in sys.argv:
        print("usage: python examples/manual_check_test.py --check")
        return 2

    print("PYDEX MANUAL CHECK")
    print("==================")

    with tempfile.TemporaryDirectory() as tmp:
        _build_project(tmp)

        report = pydex_ge.check_project(tmp)
        print("\nBroken project report:\n")
        for result in report:
            print("  ", result)
        print()

        errors = _codes(report.errors)
        warnings = _codes(report.warnings)
        missing_error = _EXPECTED_ERROR_CODES - errors
        missing_warning = _EXPECTED_WARNING_CODES - warnings

        # The valid/ subtree must be clean.
        clean_report = pydex_ge.check_all(os.path.join(tmp, "valid"))
        valid_clean = clean_report.ok

        ok = not missing_error and not missing_warning and valid_clean
        print("Expected error codes :", sorted(_EXPECTED_ERROR_CODES))
        print("Found    error codes :", sorted(errors))
        for code in sorted(missing_error):
            print("  MISSING error code:", code)
        print("Expected warning codes:", sorted(_EXPECTED_WARNING_CODES))
        print("Found    warning codes:", sorted(warnings))
        for code in sorted(missing_warning):
            print("  MISSING warning code:", code)
        print("Valid project stayed clean:", valid_clean)
        print()
        print("RESULT:", "OK" if ok else "FAILED")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())