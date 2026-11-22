import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_KEYS = {
    "client_id",
    "segment",
    "raw_shortfall",
    "net_shortfall",
    "applicable_slab_pct",
    "penalty_amount",
}


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "client_short_allocation.cli", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )


def test_cli_emits_required_decimal_string_fields() -> None:
    result = _run_cli(
        "--client-id",
        "CLIENT",
        "--segment",
        "CASH",
        "--peak-margin-required",
        "100000",
        "--allocated-collateral",
        "80000",
        "--grace-limit-pct",
        "10",
    )

    assert result.returncode == 0
    response = json.loads(result.stdout)
    assert set(response) == EXPECTED_KEYS
    assert response == {
        "client_id": "CLIENT",
        "segment": "CASH",
        "raw_shortfall": "20000",
        "net_shortfall": "10000",
        "applicable_slab_pct": "0.5",
        "penalty_amount": "50.00",
    }
    assert result.stderr == ""


def test_cli_grace_is_optional_and_equal_invocations_are_deterministic() -> None:
    arguments = (
        "--client-id",
        "CLIENT",
        "--segment",
        "FO",
        "--peak-margin-required",
        "100000",
        "--allocated-collateral",
        "80000",
    )
    first = _run_cli(*arguments)
    second = _run_cli(*arguments)

    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["net_shortfall"] == "20000"


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        (
            (
                "--client-id",
                "CLIENT",
                "--segment",
                "CASH",
                "--peak-margin-required",
                "not-a-decimal",
                "--allocated-collateral",
                "0",
            ),
            "peak_margin_required",
        ),
        (
            (
                "--client-id",
                "CLIENT",
                "--segment",
                "EQUITY",
                "--peak-margin-required",
                "10",
                "--allocated-collateral",
                "0",
            ),
            "segment",
        ),
    ],
)
def test_cli_invalid_input_exits_without_success_result(
    arguments: tuple[str, ...],
    field: str,
) -> None:
    result = _run_cli(*arguments)

    assert result.returncode != 0
    assert result.stdout == ""
    assert field in result.stderr


def test_cli_missing_required_flag_reports_the_flag() -> None:
    result = _run_cli(
        "--client-id",
        "CLIENT",
        "--segment",
        "CASH",
        "--peak-margin-required",
        "10",
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "--allocated-collateral" in result.stderr
