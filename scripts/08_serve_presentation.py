#!/usr/bin/env python3
"""Serve the local presentation app with a tiny static HTTP server."""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRESENTATION_DIR = PROJECT_ROOT / "web" / "presentation"


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve SNV presentation app")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    args = parser.parse_args()

    os.chdir(PRESENTATION_DIR)
    server = ThreadingHTTPServer((args.host, args.port), SimpleHTTPRequestHandler)
    print(f"Serving presentation on http://{args.host}:{args.port}")
    print(f"Root: {PRESENTATION_DIR}")
    server.serve_forever()


if __name__ == "__main__":
    main()
