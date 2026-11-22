"""Command-line interface for client short allocation penalty calculations."""

import argparse
import json
import sys
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from .calculator import InvalidCalculationInput, calculate_penalty


def _decimal_argument(field: str):
    def parse(value: str) -> Decimal:
        try:
            return Decimal(value)
        except InvalidOperation as error:
            raise argparse.ArgumentTypeError(
                f"{field} must be a valid decimal"
            ) from error

    return parse


def _json_value(value: str | Decimal) -> str:
    if isinstance(value, Decimal):
        if value == Decimal(0):
            return "0"
        formatted = format(value, "f")
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return formatted
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calculate a client's short allocation penalty."
    )
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--segment", choices=("CASH", "FO"), required=True)
    parser.add_argument(
        "--peak-margin-required",
        required=True,
        type=_decimal_argument("peak_margin_required"),
    )
    parser.add_argument(
        "--allocated-collateral",
        required=True,
        type=_decimal_argument("allocated_collateral"),
    )
    parser.add_argument(
        "--grace-limit-pct",
        default=Decimal("0.0"),
        type=_decimal_argument("grace_limit_pct"),
    )
    arguments = parser.parse_args(argv)

    try:
        result = calculate_penalty(
            client_id=arguments.client_id,
            segment=arguments.segment,
            peak_margin_required=arguments.peak_margin_required,
            allocated_collateral=arguments.allocated_collateral,
            grace_limit_pct=arguments.grace_limit_pct,
        )
    except InvalidCalculationInput as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    serialized = {
        key: (
            format(value, ".2f")
            if key == "penalty_amount"
            else format(value, "f")
            if key == "applicable_slab_pct"
            else _json_value(value)
        )
        for key, value in result.items()
    }
    print(json.dumps(serialized, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
