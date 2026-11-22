# Interface Contracts

## Command-Line Interface

One natural-language query is submitted per invocation:

```text
python -m ai_query_assistant --query "Why is member ACME short in CASH?"
```

The query flag is required. A successful invocation writes one JSON object conforming to the eight-field schema in [spec.md](../spec.md#output-schema-contract) to standard output. It writes no prose before or after the JSON object. Clarification requests are successful contract responses with `clarification_required: true`.

Operational failures, including local model unavailability, malformed model output, and invalid input, must be reported explicitly and must not emit a success-shaped JSON object. The exact error wording and non-zero status code are not part of the response contract.

## Local Ollama Boundary

- Use the configured local Ollama service with model `qwen2.5:3b`.
- Send only the current inquiry and the minimum context required for extraction/explanation.
- Do not use any hosted model or remote fallback.
- Treat all model output as untrusted text until parsed and validated.
- A local inference call may produce candidate extracted facts and explanation text; it cannot perform authoritative financial calculations or input validation.
- If the service is unreachable, times out, returns malformed data, or uses an unexpected model, report an explicit operational failure.

## Deterministic Calculation Boundary

The calculation component has no I/O and accepts validated `Decimal` values. It returns net shortfall, applicable slab, and severity using the rules in the specification. It must not call Ollama, convert amounts through binary floating-point, or round intermediate shortfall/grace values.

## Successful Response

The response contains exactly `member_code`, `segment`, `shortfall_amount`, `penalty_slab`, `explanation`, `remediation_action`, `severity`, and `clarification_required`. Decimal money is serialized as a base-10 string. Nulls, enums, and cross-field conditions follow the schema and structural invariants in the specification.

## Web Query API

The loopback-only browser endpoint accepts one free-form inquiry at a time at
`POST /api/query`. The inquiry may contain multiple related shortfall, grace,
or penalty-slab questions. A successful response contains exactly `answer`
and `calculation`: `answer` is a non-empty, grounded text answer, while
`calculation` is `null` for general rule questions or the eight-field
calculation response above when client facts are supplied.

## Testing Interfaces

- Unit tests call the parser normalization, Decimal calculation, and response validation independently.
- Contract tests validate exact response fields, types, enum values, nullability, and cross-field invariants.
- Integration tests replace the local Ollama boundary with a deterministic fake response; no live service is required for the default test suite.
- A separately invoked evaluation run uses the designated evaluation dataset and reports the weighted aggregate score and hard-guardrail results.
