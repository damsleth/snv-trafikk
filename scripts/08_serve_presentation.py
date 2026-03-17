#!/usr/bin/env python3
"""Serve the local presentation app with a tiny static HTTP server."""

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRESENTATION_DIR = PROJECT_ROOT / "web" / "presentation"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.patched_run import run_patched_scenario


class PresentationRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._respond_json(200, {"ok": True})
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/patched-run":
            self.send_error(404, "Unknown API endpoint")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length) or b"{}")
            package = payload.get("package") or {}
            response = run_patched_scenario(
                package=package,
                family=str(payload.get("family") or package.get("family") or ""),
                period=str(payload.get("period") or ""),
                concert=bool(payload.get("concert")),
                seed=int(payload.get("seed", 1)),
            )
            self._respond_json(200, response)
        except (BrokenPipeError, ConnectionResetError):
            return
        except ValueError as exc:
            self._respond_json(400, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive API boundary
            self._respond_json(500, {"error": str(exc)})

    def _respond_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve SNV presentation app")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    args = parser.parse_args()

    def handler(*handler_args, **handler_kwargs):
        return PresentationRequestHandler(*handler_args, directory=str(PRESENTATION_DIR), **handler_kwargs)

    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving presentation on http://{args.host}:{args.port}")
    print(f"Root: {PRESENTATION_DIR}")
    print("API: POST /api/patched-run")
    server.serve_forever()


if __name__ == "__main__":
    main()
