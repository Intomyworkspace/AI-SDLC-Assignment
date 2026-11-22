import json
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import urlsplit

import pytest

from client_short_allocation.web import CalculationRequestHandler


@pytest.fixture
def web_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), CalculationRequestHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()
    server.server_close()


def _request(
    base_url: str,
    method: str,
    path: str,
    body: dict[str, Any] | str | None = None,
) -> tuple[int, bytes, str]:
    address = urlsplit(base_url)
    connection = HTTPConnection(address.hostname, address.port)
    encoded = (
        json.dumps(body).encode("utf-8")
        if isinstance(body, dict)
        else body.encode("utf-8")
        if isinstance(body, str)
        else None
    )
    headers = {"Content-Type": "application/json"} if encoded is not None else {}
    connection.request(method, path, body=encoded, headers=headers)
    response = connection.getresponse()
    response_body = response.read()
    content_type = response.getheader("Content-Type", "")
    connection.close()
    return response.status, response_body, content_type


def test_web_page_is_served(web_server: str) -> None:
    status, body, content_type = _request(web_server, "GET", "/")

    assert status == 200
    assert content_type.startswith("text/html")
    assert b"Short allocation penalty" in body
    assert b"calculation-form" in body


def test_web_calculation_returns_exact_result_and_defaults_grace(
    web_server: str,
) -> None:
    status, body, content_type = _request(
        web_server,
        "POST",
        "/api/calculate",
        {
            "client_id": "CLIENT",
            "segment": "CASH",
            "peak_margin_required": "100000",
            "allocated_collateral": "80000",
        },
    )

    assert status == 200
    assert content_type.startswith("application/json")
    assert json.loads(body) == {
        "client_id": "CLIENT",
        "segment": "CASH",
        "raw_shortfall": "20000",
        "net_shortfall": "20000",
        "applicable_slab_pct": "0.5",
        "penalty_amount": "100.00",
    }


@pytest.mark.parametrize(
    ("body", "error_field"),
    [
        (
            {
                "client_id": "CLIENT",
                "segment": "CASH",
                "peak_margin_required": "NaN",
                "allocated_collateral": "0",
                "grace_limit_pct": "0",
            },
            "peak_margin_required",
        ),
        ("not-json", "valid JSON"),
    ],
)
def test_web_rejects_invalid_input_without_returning_a_result(
    web_server: str,
    body: dict[str, Any] | str,
    error_field: str,
) -> None:
    status, response_body, content_type = _request(
        web_server, "POST", "/api/calculate", body
    )

    assert status == 400
    assert content_type.startswith("application/json")
    assert error_field in json.loads(response_body)["error"]
