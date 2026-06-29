#!/usr/bin/env python
#
# OpenStatz CLI entry point. Kept dependency-light: the `serve` subcommand
# imports FastAPI/uvicorn lazily so that `openstatz --help` works even when the
# optional `[app]` extra is not installed.
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openstatz",
        description="OpenStatz - portfolio analytics for quants.",
    )
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Run the OpenStatz web API server (needs [app] extra).")
    serve.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    serve.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000).")
    serve.add_argument("--reload", action="store_true", help="Enable auto-reload (dev).")

    sub.add_parser("version", help="Print the OpenStatz version and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "version" or args.command is None and "--version" in (argv or sys.argv[1:]):
        from openstatz import __version__

        print(f"openstatz {__version__}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn  # noqa: F401
        except ImportError:
            print(
                "The 'serve' command requires the optional web extra. "
                "Install it with:  pip install 'openstatz[app]'",
                file=sys.stderr,
            )
            return 1

        from openstatz.app.server import run_server

        run_server(host=args.host, port=args.port, reload=args.reload)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
