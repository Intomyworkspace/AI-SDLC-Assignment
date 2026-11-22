"""Local web interface for the shortfall assistant."""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from assistant import AssistantError, OllamaClient
from prediction_generator import answer_query

HOST = "127.0.0.1"
DEFAULT_PORT = 8000
MAX_REQUEST_BYTES = 16_384
INDEX_PATH = Path(__file__).with_name("web") / "index.html"


class RequestHandler(BaseHTTPRequestHandler):
    """Serve the browser form and process one inquiry per request."""

    def _send_json(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/":
            self.send_error(404)
            return

        try:
            body = INDEX_PATH.read_bytes()
        except OSError as error:
            print(f"Could not read web interface: {error}", file=sys.stderr)
            self.send_error(500, "Web interface is unavailable")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/query":
            self._send_json(404, {"error": "Not found"})
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(415, {"error": "Content-Type must be application/json"})
            return

        content_length = self.headers.get("Content-Length")
        try:
            request_length = int(content_length) if content_length is not None else -1
        except ValueError:
            request_length = -1
        if request_length < 0:
            self._send_json(400, {"error": "A valid Content-Length is required"})
            return
        if request_length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Inquiry is too large"})
            return

        try:
            payload = json.loads(self.rfile.read(request_length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Request body must be a JSON object"})
            return

        query = payload.get("query")
        if not isinstance(query, str) or not query.strip():
            self._send_json(400, {"error": "query must be a non-empty string"})
            return

        try:
            facts = OllamaClient().extract_facts(query)
            response = answer_query(query, facts)
        except (AssistantError, ValueError) as error:
            self._send_json(502, {"error": str(error)})
            return

        self._send_json(200, response)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the local shortfall assistant web interface."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Local HTTP port (default: {DEFAULT_PORT}).",
    )
    arguments = parser.parse_args(argv)
    if not 0 < arguments.port < 65536:
        parser.error("--port must be between 1 and 65535")

    try:
        server = ThreadingHTTPServer((HOST, arguments.port), RequestHandler)
    except OSError as error:
        print(
            f"Could not start web server on {HOST}:{arguments.port}: {error}",
            file=sys.stderr,
        )
        return 2

    print(f"Open http://{HOST}:{arguments.port} in your browser.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
