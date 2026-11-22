"""Local web interface for client short allocation penalty calculations."""

import argparse
import json
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .calculator import InvalidCalculationInput, calculate_penalty

_PAGE = Path(__file__).with_name("web") / "index.html"
_MAX_REQUEST_BYTES = 16_384


def _decimal_field(payload: dict[str, Any], field: str) -> Decimal:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InvalidCalculationInput(f"{field} must be provided as decimal text")
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise InvalidCalculationInput(f"{field} must be a valid decimal") from error


def _calculate_request(payload: Any) -> dict[str, str | Decimal]:
    if not isinstance(payload, dict):
        raise InvalidCalculationInput("request body must be a JSON object")

    grace_limit_pct = (
        _decimal_field(payload, "grace_limit_pct")
        if "grace_limit_pct" in payload
        else Decimal(0)
    )
    return calculate_penalty(
        client_id=payload.get("client_id"),
        segment=payload.get("segment"),
        peak_margin_required=_decimal_field(payload, "peak_margin_required"),
        allocated_collateral=_decimal_field(payload, "allocated_collateral"),
        grace_limit_pct=grace_limit_pct,
    )


def _serialize_result(result: dict[str, str | Decimal]) -> dict[str, str]:
    serialized = {}
    for key, value in result.items():
        if key == "penalty_amount":
            serialized[key] = format(value, ".2f")
        elif key == "applicable_slab_pct":
            serialized[key] = format(value, "f")
        elif isinstance(value, Decimal):
            formatted = format(value, "f")
            serialized[key] = (
                formatted.rstrip("0").rstrip(".")
                if "." in formatted
                else formatted
            )
        else:
            serialized[key] = value
    return serialized


class CalculationRequestHandler(BaseHTTPRequestHandler):
    """Serve the calculation page and its JSON endpoint."""

    def _send_json(self, status: int, body: dict[str, str]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if urlsplit(self.path).path not in {"/", "/index.html"}:
            self.send_error(404)
            return

        page = _PAGE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/calculate":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > _MAX_REQUEST_BYTES:
                raise InvalidCalculationInput("request body size is invalid")
            payload = json.loads(self.rfile.read(content_length))
            result = _calculate_request(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "request body must contain valid JSON"})
            return
        except (InvalidCalculationInput, ValueError) as error:
            self._send_json(400, {"error": str(error)})
            return

        self._send_json(200, _serialize_result(result))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the client short allocation penalty web interface."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()

    with ThreadingHTTPServer(
        (arguments.host, arguments.port), CalculationRequestHandler
    ) as server:
        print(f"Open http://{arguments.host}:{arguments.port} in your browser.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nWeb interface stopped.")


if __name__ == "__main__":
    main()
