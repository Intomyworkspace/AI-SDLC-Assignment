from decimal import Decimal

import pytest

from client_short_allocation import InvalidCalculationInput, calculate_penalty


def _valid_request() -> dict[str, object]:
    return {
        "client_id": "CLIENT-VALID",
        "segment": "CASH",
        "peak_margin_required": Decimal(100),
        "allocated_collateral": Decimal(50),
        "grace_limit_pct": Decimal(0),
    }


@pytest.mark.parametrize("client_id", ["", "   ", None, 123])
def test_rejects_empty_or_non_string_client_id(client_id: object) -> None:
    request = _valid_request()
    request["client_id"] = client_id

    with pytest.raises(InvalidCalculationInput, match="client_id"):
        calculate_penalty(**request)  # type: ignore[arg-type]


@pytest.mark.parametrize("segment", ["cash", "EQUITY", "", None])
def test_rejects_unsupported_segment(segment: object) -> None:
    request = _valid_request()
    request["segment"] = segment

    with pytest.raises(InvalidCalculationInput, match="segment"):
        calculate_penalty(**request)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("peak_margin_required", Decimal("-0.01")),
        ("allocated_collateral", Decimal("-0.01")),
        ("grace_limit_pct", Decimal("-0.01")),
        ("peak_margin_required", 1),
        ("allocated_collateral", 1.0),
        ("grace_limit_pct", "1.0"),
    ],
)
def test_rejects_negative_or_non_decimal_values(field: str, value: object) -> None:
    request = _valid_request()
    request[field] = value

    with pytest.raises(InvalidCalculationInput, match=field):
        calculate_penalty(**request)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
@pytest.mark.parametrize(
    "field",
    ["peak_margin_required", "allocated_collateral", "grace_limit_pct"],
)
def test_rejects_non_finite_decimal_values(field: str, value: Decimal) -> None:
    request = _valid_request()
    request[field] = value

    with pytest.raises(InvalidCalculationInput, match=field):
        calculate_penalty(**request)  # type: ignore[arg-type]
