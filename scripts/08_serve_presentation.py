#!/usr/bin/env python3
"""Serve the local presentation app with a tiny static HTTP server."""

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import sys
from urllib.parse import urlparse


from config import PROJECT_ROOT

PRESENTATION_DIR = PROJECT_ROOT / "web" / "presentation"
MAX_PATCHED_RUN_BYTES = 2 * 1024 * 1024
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self' https://unpkg.com; style-src 'self' 'unsafe-inline' https://unpkg.com; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.patched_run import run_patched_scenario


class PresentationRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        for header, value in SECURITY_HEADERS.items():
            self.send_header(header, value)
        super().end_headers()

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
            if content_length > MAX_PATCHED_RUN_BYTES:
                self._respond_json(413, {"error": "Request body is too large"})
                return
            payload = json.loads(self.rfile.read(content_length) or b"{}")
            validate_patched_run_payload(payload)
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


def validate_patched_run_payload(payload: dict) -> None:
    """Validate the small JSON envelope accepted by /api/patched-run."""
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object")
    package = payload.get("package") or {}
    if not isinstance(package, dict):
        raise ValueError("package must be a JSON object")
    if "seed" in payload:
        seed = int(payload["seed"])
        if seed < 1 or seed > 100:
            raise ValueError("seed must be between 1 and 100")
    if "period" in payload and payload["period"] not in {"", "morning", "afternoon", "midday"}:
        raise ValueError("period must be morning, afternoon, or midday")
    for key in ["edges", "artifacts"]:
        if key in package and not isinstance(package[key], (dict, list)):
            raise ValueError(f"package.{key} has an invalid shape")


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
