# Data Model: Client Short Allocation & Penalty Calculation

The calculation is stateless. A request produces one result; neither entity is persisted.

## Calculation Request

| Field | Type | Required | Validation / meaning |
|---|---|---:|---|
| `client_id` | string | Yes | Must not be empty or whitespace-only. Treat as opaque and preserve its value. |
| `segment` | string | Yes | Must be exactly `CASH` or `FO`. |
| `peak_margin_required` | `Decimal` | Yes | Must be finite and greater than or equal to zero; INR. |
| `allocated_collateral` | `Decimal` | Yes | Must be finite and greater than or equal to zero; INR. |
| `grace_limit_pct` | `Decimal` | No | Must be finite and greater than or equal to zero; percentage. Defaults to exact decimal zero. |

Library callers provide `Decimal` instances for numeric fields. The library rejects floats and other numeric types rather than coercing them. CLI callers provide decimal text, which is parsed directly as `Decimal`.

## Calculation Result

The library returns a structured mapping containing exactly these fields:

| Field | Type | Meaning |
|---|---|---|
| `client_id` | string | The request's client identifier. |
| `segment` | string | The request's segment. |
| `raw_shortfall` | `Decimal` | `max(0, peak_margin_required - allocated_collateral)`. |
| `net_shortfall` | `Decimal` | `max(0, raw_shortfall - peak_margin_required * (grace_limit_pct / 100))`. |
| `applicable_slab_pct` | `Decimal` | The rate selected using net shortfall: 0.0, 0.5, 1.0, or 5.0. |
| `penalty_amount` | `Decimal` | Net shortfall multiplied by the applicable rate divided by 100, quantized to INR 0.01 using `ROUND_HALF_UP`. |

### Slab selection

| Net shortfall (INR) | Rate |
|---:|---:|
| Equal to zero | 0.0% |
| Greater than zero through 100000 inclusive | 0.5% |
| Greater than 100000 through 1000000 inclusive | 1.0% |
| Greater than 1000000 | 5.0% |

No intermediate shortfall or grace value is rounded. Only the final penalty amount is rounded.

## Validation Errors

Invalid request values raise a clear custom validation exception identifying the invalid field. The CLI reports invalid values to standard error, exits non-zero, and does not emit a successful result.

## Relationships and lifecycle

A request has one corresponding result. There are no cross-request relationships, persistence lifecycle, or mutable state.
