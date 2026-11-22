# Quickstart: Validate the Calculation

## Prerequisites

- Python 3.10 or later.
- `pytest`, `ruff`, and `bandit` available in the development/CI environment. These are test and quality-gate tools; the application runtime uses only the Python standard library.
- Run commands from the repository root.

## Run a representative calculation

```sh
python -m client_short_allocation.cli \
  --client-id CLIENT \
  --segment CASH \
  --peak-margin-required 100000 \
  --allocated-collateral 80000 \
  --grace-limit-pct 10
```

Expected JSON values:

```json
{
  "client_id": "CLIENT",
  "segment": "CASH",
  "raw_shortfall": "20000",
  "net_shortfall": "10000",
  "applicable_slab_pct": "0.5",
  "penalty_amount": "50.00"
}
```

## Use the web interface

Start the local web UI from the `part1a` directory:

```sh
python -m client_short_allocation.web
```

Open the printed address (by default, `http://127.0.0.1:8000`) in a browser. Enter the client ID, segment, margin, collateral, and optional grace percentage, then select **Calculate penalty**. The UI sends decimal text to the same calculation library used by the CLI.

## Validate the contract and edge cases

The unit and CLI contract suites must cover:

- Zero, exact 100000 INR, 100000.01 INR, exact 1000000 INR, and 1000000.01 INR net shortfalls.
- Grace omitted, zero grace, grace exactly offsetting shortfall, and grace exceeding shortfall.
- A ROUND_HALF_UP tie, such as a net shortfall of 1 INR at 0.5%, producing a penalty of `0.01`.
- Invalid segment, blank client identifier, negative amounts, malformed decimal text, non-finite Decimal values, and non-Decimal library numeric inputs.
- Exact result keys and Decimal-preserving JSON strings; repeated equal inputs produce equal output.

## Run quality gates

```sh
python -m pytest
ruff check client_short_allocation tests
bandit -r client_short_allocation
```

Each command must complete with zero errors. Invalid CLI inputs must exit non-zero, write a field-specific error to standard error, and emit no successful result object.
