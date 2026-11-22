# Data Model: AI Query & Shortfall Explanation Assistant

## Member Inquiry

Represents one natural-language request supplied to the local assistant.

| Field | Type | Constraints |
|---|---|---|
| `query_text` | string | Required, non-empty after trimming; processed locally; not persisted. |

## Extracted Inquiry Facts

Intermediate, untrusted facts returned by local language interpretation. They are validated before use.

| Field | Type | Constraints |
|---|---|---|
| `member_code` | string or unknown | Non-empty if identified; never guessed. |
| `segment` | `CASH`, `FO`, or unknown | Only these values are accepted; ambiguous or missing values require clarification. |
| `peak_margin_required` | Decimal or unknown | Finite and non-negative when present. |
| `allocated_collateral` | Decimal or unknown | Finite and non-negative when present. |
| `grace_limit_pct` | Decimal or unknown | Finite and non-negative when present; defaults to exact zero only when the inquiry's calculation semantics allow the default. |
| `shortfall_amount` | Decimal or unknown | A directly stated net chargeable shortfall may be used; an explicitly raw/gross value is not treated as net. |
| `evidence` | text references | Identify the source portion of the inquiry for each extracted value; do not add facts not found in the inquiry. |

Model-produced monetary values are parsed from base-10 text into `Decimal`; binary floating-point conversion is prohibited. Any malformed, negative, or non-finite value is invalid and cannot be used in a calculation.

## Calculation Result

Represents deterministic derived financial values.

| Field | Type | Constraints |
|---|---|---|
| `raw_shortfall` | Decimal | `max(0, peak_margin_required - allocated_collateral)`. |
| `allowable_grace` | Decimal | `peak_margin_required * (grace_limit_pct / 100)`. |
| `net_shortfall` | Decimal | `max(0, raw_shortfall - allowable_grace)`; this supplies the response's `shortfall_amount`. |
| `penalty_slab` | enum | `0.0%` at zero; `0.5%` for `(0, 100000]`; `1.0%` for `(100000, 1000000]`; `5.0%` above `1000000` INR. |
| `severity` | enum | `LOW` for zero or 0.5%; `MEDIUM` for 1.0%; `HIGH` for 5.0%. |

If the inquiry provides a clear net shortfall directly, the system may determine the slab from that value without reconstructing the gross margin inputs. A directly stated raw/gross shortfall with insufficient grace details does not determine the net shortfall and requires clarification.

## Assistant Response

The public response is defined by the schema in [spec.md](./spec.md#output-schema-contract) and contains exactly:

| Field | Type | Nullability |
|---|---|---|
| `member_code` | string | `null` if unknown or clarification is required. |
| `segment` | `CASH` or `FO` | `null` if unknown or clarification is required. |
| `shortfall_amount` | base-10 decimal string | `null` if it cannot be reliably determined. |
| `penalty_slab` | enumerated percentage string | `null` if it cannot be reliably determined. |
| `explanation` | non-empty string | Never null; asks for missing information when needed. |
| `remediation_action` | non-empty string | Never null; may request clarification. |
| `severity` | `LOW`, `MEDIUM`, `HIGH`, or `UNKNOWN` | `UNKNOWN` when it cannot be reliably assessed. |
| `clarification_required` | boolean | True when identity, segment, or required calculation information is missing or ambiguous. |

## Web Query Response

The web endpoint wraps a user-facing `answer` string and an optional
`calculation`. General rule questions have `calculation: null`; when client
facts are supplied, `calculation` follows the Assistant Response contract.
One inquiry can contain multiple related topics, but no client state is
carried between requests.

## State and Invariants

- The assistant handles one request at a time; there is no persisted conversation or member state.
- If member code or segment is missing or ambiguous, clarification is mandatory even if financial amounts are present.
- If `clarification_required` is false, member code, segment, shortfall amount, and penalty slab are all present.
- Every non-null shortfall is finite, non-negative, and represented as exact decimal text at the JSON boundary.
- A slab and severity are derived from the validated net shortfall, never copied from unverified model output.
- An operational failure is not an `Assistant Response` and must not be encoded as a successful response with invented values.
