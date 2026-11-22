"""Exact Decimal calculation for client short allocation penalties."""

from decimal import MAX_EMAX, MIN_EMIN, ROUND_HALF_UP, Decimal, localcontext

_CENT = Decimal("0.01")
_ZERO = Decimal(0)


class InvalidCalculationInput(ValueError):
    """Raised when a calculation request contains an invalid field."""


def _validate_request(
    client_id: str,
    segment: str,
    peak_margin_required: Decimal,
    allocated_collateral: Decimal,
    grace_limit_pct: Decimal,
) -> None:
    if not isinstance(client_id, str) or not client_id.strip():
        raise InvalidCalculationInput("client_id must be a non-empty string")
    if not isinstance(segment, str) or segment not in {"CASH", "FO"}:
        raise InvalidCalculationInput("segment must be either CASH or FO")

    for field, value in (
        ("peak_margin_required", peak_margin_required),
        ("allocated_collateral", allocated_collateral),
        ("grace_limit_pct", grace_limit_pct),
    ):
        if not isinstance(value, Decimal):
            raise InvalidCalculationInput(f"{field} must be a Decimal")
        if not value.is_finite():
            raise InvalidCalculationInput(f"{field} must be finite")
        if value < _ZERO:
            raise InvalidCalculationInput(f"{field} must be non-negative")


def _calculation_settings(
    peak_margin_required: Decimal,
    allocated_collateral: Decimal,
    grace_limit_pct: Decimal,
) -> tuple[int, int, int]:
    participating = [
        value
        for value in (peak_margin_required, allocated_collateral)
        if value != _ZERO
    ]
    if peak_margin_required != _ZERO and grace_limit_pct != _ZERO:
        participating.append(grace_limit_pct)

    if not participating:
        return 28, 0, -2

    highest_adjusted = max(value.adjusted() for value in participating)
    lowest_exponent = min(value.as_tuple().exponent for value in participating)
    if peak_margin_required != _ZERO and grace_limit_pct != _ZERO:
        highest_adjusted = max(
            highest_adjusted,
            peak_margin_required.adjusted() + grace_limit_pct.adjusted() + 1,
        )
        lowest_exponent = min(
            lowest_exponent,
            peak_margin_required.as_tuple().exponent
            + grace_limit_pct.as_tuple().exponent
            - 2,
        )

    lowest_place = min(lowest_exponent, -2)
    coefficient_digits = sum(
        len(value.as_tuple().digits) for value in participating
    )
    precision = max(
        28,
        highest_adjusted - lowest_place + coefficient_digits + 12,
        max(highest_adjusted, 0) + 4,
    )
    return precision, highest_adjusted, lowest_place


def calculate_penalty(
    client_id: str,
    segment: str,
    peak_margin_required: Decimal,
    allocated_collateral: Decimal,
    grace_limit_pct: Decimal = Decimal("0.0"),
) -> dict[str, str | Decimal]:
    """Calculate a client's shortfall and applicable penalty."""
    _validate_request(
        client_id,
        segment,
        peak_margin_required,
        allocated_collateral,
        grace_limit_pct,
    )
    precision, highest_adjusted, lowest_place = _calculation_settings(
        peak_margin_required,
        allocated_collateral,
        grace_limit_pct,
    )
    with localcontext() as context:
        context.prec = precision
        context.Emax = min(MAX_EMAX, max(context.Emax, highest_adjusted + 2))
        context.Emin = max(
            MIN_EMIN,
            min(context.Emin, lowest_place - precision - 2),
        )
        raw_shortfall = max(
            _ZERO,
            peak_margin_required - allocated_collateral,
        )
        allowable_grace = peak_margin_required * (grace_limit_pct / Decimal(100))
        net_shortfall = max(_ZERO, raw_shortfall - allowable_grace)

        if net_shortfall == _ZERO:
            applicable_slab_pct = Decimal("0.0")
        elif net_shortfall <= Decimal(100000):
            applicable_slab_pct = Decimal("0.5")
        elif net_shortfall <= Decimal(1000000):
            applicable_slab_pct = Decimal("1.0")
        else:
            applicable_slab_pct = Decimal("5.0")

        penalty_amount = (
            net_shortfall * applicable_slab_pct / Decimal(100)
        ).quantize(_CENT, rounding=ROUND_HALF_UP)

        return {
            "client_id": client_id,
            "segment": segment,
            "raw_shortfall": raw_shortfall,
            "net_shortfall": net_shortfall,
            "applicable_slab_pct": applicable_slab_pct,
            "penalty_amount": penalty_amount,
        }
