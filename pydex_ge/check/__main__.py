"""Command-line entry point for the PYDEX project checker.

Usage::

    python -m pydex_ge.check [path] [options]

Modes (default: ``--all``):

    --python   syntax, imports, and undefined names
    --assets   asset paths, dynamic paths, duplicate assets
    --pydex_ge    PYDEX API / configuration / scene mistakes
    --all      every check (same as no mode flag)

Output options:

    --quiet    no problem list, only the summary block
    --warnings include warning-severity problems in the list (default on);
               pass --no-warnings to hide them
    --json     machine-readable JSON instead of the text report

Exit code is 0 when no errors are found, 1 when errors are found, and 2
when the path does not exist.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from ._models import CheckReport


def _banner() -> None:
    print("PYDEX PROJECT CHECK")
    print("=" * 60)


def _build_report(target: str, mode: str) -> CheckReport:
    from . import check_all, check_assets, check_file, check_pydex, check_python

    if mode == "python":
        return check_python(target)
    if mode == "assets":
        return check_assets(target)
    if mode == "pydex_ge":
        return check_pydex(target)
    if os.path.isdir(target):
        return check_all(target)
    return CheckReport(check_file(target), root=target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pydex_ge.check",
        description="Static PYDEX project checker (headless, safe).",
    )
    parser.add_argument("path", nargs="?", default=".", help="file or folder")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--python", action="store_true", help="python checks only")
    mode.add_argument("--assets", action="store_true", help="asset checks only")
    mode.add_argument("--pydex_ge", action="store_true", help="PYDEX API checks only")
    mode.add_argument("--all", action="store_true", help="run every check (default)")
    parser.add_argument("--quiet", action="store_true", help="summary only")
    parser.add_argument(
        "--warnings",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include warnings (use --no-warnings to hide them)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    selected = "all"
    for name, flag in (("python", args.python), ("assets", args.assets),
                       ("pydex_ge", args.pydex_ge), ("all", args.all)):
        if flag:
            selected = name
            break

    target = os.path.abspath(args.path)
    if not os.path.exists(target):
        print(f"PYDEX CHECK: path does not exist: {target}", file=sys.stderr)
        return 2

    report = _build_report(target, selected)
    if args.json:
        payload = report.to_dict()
        payload["root"] = target
        print(json.dumps(payload, indent=2))
        return 0 if report.ok else 1

    _banner()
    print(f"Scanning : {target}")
    print(f"Mode     : {selected}")
    print()

    sections = [
        ("ERRORS", report.errors),
        ("WARNINGS", report.warnings if args.warnings else []),
        ("INFO", report.infos if not args.quiet else []),
    ]
    for title, items in sections:
        if not items:
            continue
        if args.quiet and title == "ERRORS":
            print(f"{title} ({len(items)})")
            for item in items:
                loc = item.path
                if item.lineno is not None:
                    loc += f":{item.lineno}"
                    if item.column is not None:
                        loc += f":{item.column}"
                print(f"  x {loc}  [{item.code}] {item.message}")
            continue
        if args.quiet:
            continue
        print(title)
        print("-" * 60)
        from ._format import render_result

        for item in items:
            print(render_result(item))
            print()

    print("SUMMARY")
    print("-" * 60)
    print(f"Problems     : {len(report)}")
    print(f"Errors       : {len(report.errors)}")
    print(f"Warnings     : {len(report.warnings)}")
    print(f"Info         : {len(report.infos)}")
    print()
    if report.ok:
        print("OK - no errors found.")
        return 0
    print(f"{len(report.errors)} error(s) found - fix and re-run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())