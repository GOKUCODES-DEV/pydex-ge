"""Command-line entry point for dex-editor.

``python -m pydex_ge.editor create <dir> "<name>"``  creates a project.
``python -m pydex_ge.editor <dir>``                     opens an editor on it.
"""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dex-editor",
        description="PYDEX project editor (shipped inside the pydex_ge package).",
    )
    sub = parser.add_subparsers(dest="command")

    create = sub.add_parser("create", help="create a new empty project")
    create.add_argument("directory", help="directory to create the project in")
    create.add_argument(
        "name", nargs="?", default="My Game", help="project name (used in code)"
    )

    sub.add_parser("open", help="open an existing project").add_argument(
        "directory", help="project directory"
    )

    # Bare-directory shorthand: ``dex-editor path/to/project`` (and the
    # ``python -m pydex_ge.editor <dir>`` form) mean the same as ``open <dir>``.
    # Rewrite the argv before parsing so the positional can never shadow a
    # subcommand choice.
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("create", "open") and not argv[0].startswith("-"):
        argv = ["open", *argv]

    args = parser.parse_args(argv)

    from . import project as project_module
    from .project import DexProject

    try:
        if args.command == "create":
            root = os.path.abspath(args.directory)
            try:
                existing = DexProject.load(root)
            except project_module.ConfigurationError:
                existing = None
            if existing is not None:
                print(f"Project already exists at {root}; opening it.")
            else:
                project = DexProject.create_empty(root, args.name)
                print(f"Created project {project.name!r} at {root}")
                print(f"  manifest:  {project.manifest_path}")
                print(f"  main.py:   {project.main_path}")
                return 0
        elif args.command == "open":
            root = os.path.abspath(args.directory)
            if not os.path.isdir(root):
                print(f"Directory not found: {root}", file=sys.stderr)
                return 1
        else:
            parser.print_help()
            return 2

        project = DexProject.load(root)
        from . import Editor

        Editor(project).run()
        return 0
    except (project_module.ConfigurationError, OSError, ValueError) as exc:
        print(f"dex-editor: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())