from decimal import Decimal, getcontext, localcontext

import pytest

from client_short_allocation import calculate_penalty

EXPECTED_KEYS = {
    "client_id",
    "segment",
    "raw_shortfall",
    "net_shortfall",
    "applicable_slab_pct",
    "penalty_amount",
}


def test_calculates_raw_and_grace_adjusted_shortfall() -> None:
    result = calculate_penalty(
        "CLIENT-1",
        "CASH",
        Decimal(100000),
        Decimal(80000),
        Decimal(10),
    )

    assert result == {
        "client_id": "CLIENT-1",
        "segment": "CASH",
        "raw_shortfall": Decimal(20000),
        "net_shortfall": Decimal(10000),
        "applicable_slab_pct": Decimal("0.5"),
        "penalty_amount": Decimal("50.00"),
    }
    assert set(result) == EXPECTED_KEYS


def test_grace_defaults_to_zero_and_over_allocation_has_no_penalty() -> None:
    result = calculate_penalty(
        "CLIENT-2",
        "FO",
        Decimal(100),
        Decimal(150),
    )

    assert result["raw_shortfall"] == Decimal(0)
    assert result["net_shortfall"] == Decimal(0)
    assert result["applicable_slab_pct"] == Decimal("0.0")
    assert result["penalty_amount"] == Decimal("0.00")


@pytest.mark.parametrize("grace_limit_pct", [Decimal(50), Decimal(150)])
def test_grace_that_offsets_or_exceeds_shortfall_has_no_penalty(
    grace_limit_pct: Decimal,
) -> None:
    result = calculate_penalty(
        "CLIENT-GRACE",
        "CASH",
        Decimal(100),
        Decimal(50),
        grace_limit_pct,
    )

    assert result["raw_shortfall"] == Decimal(50)
    assert result["net_shortfall"] == Decimal(0)
    assert result["applicable_slab_pct"] == Decimal("0.0")
    assert result["penalty_amount"] == Decimal("0.00")


@pytest.mark.parametrize(
    ("net_shortfall", "slab_pct"),
    [
        (Decimal(0), Decimal("0.0")),
        (Decimal(100000), Decimal("0.5")),
        (Decimal("100000.01"), Decimal("1.0")),
        (Decimal(1000000), Decimal("1.0")),
        (Decimal("1000000.01"), Decimal("5.0")),
    ],
)
def test_selects_slab_at_and_around_boundaries(
    net_shortfall: Decimal,
    slab_pct: Decimal,
) -> None:
    result = calculate_penalty(
        "CLIENT-3",
        "CASH",
        net_shortfall,
        Decimal(0),
    )

    assert result["net_shortfall"] == net_shortfall
    assert result["applicable_slab_pct"] == slab_pct


def test_preserves_intermediate_decimal_precision() -> None:
    result = calculate_penalty(
        "CLIENT-4",
        "CASH",
        Decimal("1000.03"),
        Decimal("999.01"),
        Decimal("0.1"),
    )

    assert result["raw_shortfall"] == Decimal("1.02")
    assert result["net_shortfall"] == Decimal("0.01997")


def test_uses_sufficient_precision_without_changing_caller_context() -> None:
    original_precision = getcontext().prec

    with localcontext() as context:
        context.prec = 5
        result = calculate_penalty(
            "CLIENT-6",
            "CASH",
            Decimal("123456789012345678901234567890.00"),
            Decimal("0.001"),
        )
        assert result["raw_shortfall"] == Decimal("123456789012345678901234567889.999")

    assert getcontext().prec == original_precision


def test_rounds_penalty_ties_half_up() -> None:
    result = calculate_penalty(
        "CLIENT-5",
        "CASH",
        Decimal(1),
        Decimal(0),
    )

    assert result["penalty_amount"] == Decimal("0.01")
