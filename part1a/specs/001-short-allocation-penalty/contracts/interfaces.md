# Interface Contracts

## Library

Expose `calculate_penalty` with this conceptual signature:

```python
calculate_penalty(
    client_id: str,
    segment: str,
    peak_margin_required: Decimal,
    allocated_collateral: Decimal,
    grace_limit_pct: Decimal = Decimal("0.0"),
) -> dict[str, str | Decimal]
```

Return a structured mapping with exactly:

- `client_id`
- `segment`
- `raw_shortfall`
- `net_shortfall`
- `applicable_slab_pct`
- `penalty_amount`

The four numeric result fields remain `Decimal` values. Inputs and outputs follow the rules in [data-model.md](../data-model.md). Invalid inputs raise `InvalidCalculationInput`, a purpose-specific exception derived from `ValueError`. The operation has no I/O, persistence, randomness, or external calls.

## Command-line interface

One calculation is submitted per invocation:

```text
python -m client_short_allocation.cli \
  --client-id CLIENT \
  --segment CASH \
  --peak-margin-required DECIMAL \
  --allocated-collateral DECIMAL \
  [--grace-limit-pct DECIMAL]
```

The four required flags are `--client-id`, `--segment`, `--peak-margin-required`, and `--allocated-collateral`. `--grace-limit-pct` is optional and defaults to exact decimal zero. Decimal values are parsed from text without conversion through binary floating-point.

### Successful response

Write one JSON object and a newline to standard output. It contains exactly the six result keys. `client_id` and `segment` are JSON strings. Decimal fields are JSON strings in fixed-point base-10 notation, with no percent sign on the rate. `penalty_amount` always has exactly two digits after the decimal point.

Example:

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

### Invalid request

For malformed, missing, or invalid values, do not emit a success object. Report a field-specific actionable error on standard error and exit with a non-zero status. The exact non-zero status code and wording are not part of the contract.
