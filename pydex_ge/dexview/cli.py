"""Command line interface for :mod:`pydex_ge.dexview`.

Examples::

    python -m pydex_ge.dexview path/to/project
    python -m pydex_ge.dexview path/to/project --out preview
    python -m pydex_ge.dexview path/to/project --serve --port 8700
"""

from __future__ import annotations

import argparse
import os

from . import PAGE_TITLE, render_project


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pydex_ge.dexview",
        description="Render a static HTML snapshot of a dex project.",
    )
    parser.add_argument("project", help="path to the dex project directory")
    parser.add_argument(
        "--out",
        default=None,
        metavar="DIR",
        help="output directory (default: <project>/.dexview)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="serve the snapshot over HTTP and open a browser",
    )
    parser.add_argument(
        "--port", type=int, default=8700, help="port for --serve (default: 8700)"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="with --serve, do not open a browser"
    )
    return parser


def make_server(directory: str, port: int = 0):
    """Create a threaded HTTP server serving ``directory``."""
    import functools
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class ClosingHandler(SimpleHTTPRequestHandler):
        """Close the served file so Windows can reclaim it between requests."""

        def copyfile(self, source, outputfile):
            try:
                super().copyfile(source, outputfile)
            finally:
                source.close()

    handler = functools.partial(ClosingHandler, directory=directory)
    return ThreadingHTTPServer(("127.0.0.1", int(port)), handler)


def _serve(directory: str, port: int, open_browser: bool) -> int:
    import threading
    import webbrowser

    server = make_server(directory, port)
    url = f"http://127.0.0.1:{server.server_port}/"
    if open_browser:
        threading.Timer(0.2, lambda: webbrowser.open(url)).start()
    print(f"{PAGE_TITLE}: serving {directory} at {url} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out_dir = os.path.abspath(args.out) if args.out else None
    path = render_project(os.path.abspath(args.project), out_dir=out_dir)
    print(f"{PAGE_TITLE}: wrote {path}")
    if args.serve:
        return _serve(os.path.dirname(path), args.port, not args.no_browser)
    return 0
