# Feature Specification: Client Short Allocation & Penalty Calculation

**Feature Branch**: `001-short-allocation-penalty`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Build a deterministic CLI and library module for Client Short Allocation & Penalty Calculation in clearing operations. Inputs: client_id (str), segment (CASH/FO), peak_margin_required (Decimal >= 0), allocated_collateral (Decimal >= 0), grace_limit_pct (Decimal, default 0.0). Compute raw shortfall, grace amount, net chargeable shortfall, and penalty by slab. Return client_id, segment, raw_shortfall, net_shortfall, applicable_slab_pct, and penalty_amount; round penalty to 2 decimal places using ROUND_HALF_UP."

## Clarifications

### Session 2026-11-13

- Q: How should the CLI receive each calculation request? → A: Named command-line flags.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate a Client Penalty (Priority: P1)

A clearing operations user supplies a client's segment, required peak margin, collateral allocation, and optional grace percentage to determine the chargeable shortfall and applicable penalty.

**Why this priority**: Correct and reproducible penalty calculation is the feature's primary clearing-operations value.

**Independent Test**: Provide valid inputs to the calculation library and verify all six output fields against independently calculated expected values, including the applicable slab and rounded penalty.

**Acceptance Scenarios**:

1. **Given** a CASH client with required margin 100000, collateral 80000, and grace 10%, **When** the user calculates the penalty, **Then** raw shortfall is 20000, net shortfall is 10000, applicable slab is 0.5%, and penalty is 50.00.
2. **Given** a client whose allocated collateral equals or exceeds required margin, **When** the user calculates the penalty, **Then** raw and net shortfall are zero, applicable slab is 0.0%, and penalty is 0.00.
3. **Given** valid inputs with grace omitted, **When** the user calculates the penalty, **Then** grace defaults to zero and the result matches the same calculation with an explicit zero grace percentage.

### User Story 2 - Run the Calculation from the CLI (Priority: P2)

A clearing operations user runs the calculation from a command line and receives a structured JSON result suitable for review or downstream processing.

**Why this priority**: The CLI makes the same core calculation usable in operational workflows without requiring a caller to write code.

**Independent Test**: Invoke the CLI with valid input values, parse its standard output as JSON, and verify the required keys and values. Invoke it with invalid input and verify a non-zero exit status and an actionable error on standard error.

**Acceptance Scenarios**:

1. **Given** valid client and calculation inputs, **When** the user invokes the CLI, **Then** it emits one JSON object containing `client_id`, `segment`, `raw_shortfall`, `net_shortfall`, `applicable_slab_pct`, and `penalty_amount`.
2. **Given** a malformed or out-of-domain input, **When** the user invokes the CLI, **Then** it emits no success result, exits non-zero, and reports the invalid field clearly on standard error.
3. **Given** the same valid input is submitted repeatedly, **When** the user invokes the CLI, **Then** each invocation emits identical JSON values.

### User Story 3 - Reject Invalid Calculation Inputs (Priority: P1)

A library or CLI caller receives a clear validation error instead of a misleading result when required values are malformed or outside the supported domain.

**Why this priority**: Invalid clearing data must not produce a penalty that appears valid.

**Independent Test**: Exercise missing, wrong-type, non-finite, and out-of-domain values through the library and CLI, and verify each is rejected explicitly.

**Acceptance Scenarios**:

1. **Given** a negative margin or collateral, **When** the calculation is requested, **Then** the input is rejected with a field-specific validation error.
2. **Given** an unsupported segment, empty client identifier, or non-finite decimal, **When** the calculation is requested, **Then** the input is rejected and no result is returned.
3. **Given** a binary floating-point value passed to the library for a decimal input, **When** the calculation is requested, **Then** the value is rejected rather than implicitly converted.

### Edge Cases

- Required margin and collateral are both zero: all calculated shortfall and penalty values are zero.
- Collateral equals required margin: raw shortfall is zero.
- Collateral exceeds required margin: raw shortfall is clamped to zero, not negative.
- Grace is zero: net shortfall equals raw shortfall.
- Grace exactly offsets raw shortfall: net shortfall is zero and the applicable slab is 0.0%.
- Grace exceeds raw shortfall, including grace percentages greater than 100% when allowed by the stated formula: net shortfall is clamped to zero.
- Net shortfall exactly equals 100000 INR: the 0.5% slab applies.
- Net shortfall is 100000.01 INR: the 1.0% slab applies.
- Net shortfall exactly equals 1000000 INR: the 1.0% slab applies.
- Net shortfall is 1000000.01 INR: the 5.0% slab applies.
- A penalty has a fractional halpaise result: round to two decimal places using ROUND_HALF_UP (for example, 0.005 becomes 0.01).
- Inputs containing NaN, positive infinity, or negative infinity are rejected.
- A CLI decimal argument is malformed, missing, or expressed as a binary float-like value: the CLI reports the invalid input and does not emit a result.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a reusable calculation operation that accepts `client_id`, `segment`, `peak_margin_required`, `allocated_collateral`, and optional `grace_limit_pct`.
- **FR-002**: The system MUST accept only `CASH` or `FO` as segment values.
- **FR-003**: The system MUST require a non-empty, non-whitespace client identifier and finite `Decimal` values for all numeric library inputs; it MUST reject other numeric types rather than coerce them. The CLI MUST parse decimal text without passing through binary floating-point.
- **FR-004**: The system MUST require `peak_margin_required` and `allocated_collateral` to be greater than or equal to zero.
- **FR-005**: The system MUST require `grace_limit_pct` to be greater than or equal to zero; its default MUST be exact decimal zero.
- **FR-006**: The system MUST calculate `raw_shortfall` as the greater of zero and `peak_margin_required - allocated_collateral`.
- **FR-007**: The system MUST calculate the allowable grace amount as `peak_margin_required * (grace_limit_pct / 100)`.
- **FR-008**: The system MUST calculate `net_shortfall` as the greater of zero and `raw_shortfall - allowable_grace`.
- **FR-009**: The system MUST select the penalty rate using `net_shortfall`: 0.0% when it is zero; 0.5% when it is greater than zero and at most 100000 INR; 1.0% when it is greater than 100000 INR and at most 1000000 INR; and 5.0% when it is greater than 1000000 INR.
- **FR-010**: The system MUST calculate the penalty from `net_shortfall` and the selected percentage, then round the amount to two decimal places using ROUND_HALF_UP. It MUST NOT round intermediate shortfall or grace calculations.
- **FR-011**: The library MUST return a structured result containing exactly the required result fields: `client_id`, `segment`, `raw_shortfall`, `net_shortfall`, `applicable_slab_pct`, and `penalty_amount`. Numeric result values MUST remain exact decimal values in the library result.
- **FR-012**: The CLI MUST accept `--client-id`, `--segment`, `--peak-margin-required`, and `--allocated-collateral` as required named flags; it MUST accept `--grace-limit-pct` as an optional named flag and MUST emit a JSON object with the six required result fields on success.
- **FR-013**: In CLI JSON output, decimal values MUST be encoded as base-10 strings to preserve exactness; `penalty_amount` MUST have exactly two fractional digits. The selected rate MUST be represented as its numeric percentage without a percent sign.
- **FR-014**: Invalid library inputs MUST raise a clear custom validation exception. Invalid CLI inputs MUST produce a non-zero exit status and a field-specific error on standard error without emitting a success-shaped result.
- **FR-015**: For identical valid inputs, the library and CLI MUST produce identical results across repeated invocations, with no random behavior or external API calls.

### Key Entities

- **Calculation Request**: One client's clearing calculation inputs: client identifier, segment, required peak margin, allocated collateral, and optional grace percentage.
- **Calculation Result**: The client and segment identifiers, raw and net shortfall, selected slab percentage, and rounded penalty amount.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All valid test vectors produce all six required result fields with exact expected values in both library and CLI output.
- **SC-002**: 100% of boundary test vectors at zero, 100000 INR, 100000.01 INR, 1000000 INR, and 1000000.01 INR select the specified slab.
- **SC-003**: 100% of penalty rounding test vectors match two-decimal ROUND_HALF_UP outcomes, including tie cases.
- **SC-004**: Repeating a calculation with identical inputs produces identical values in 100% of determinism checks.
- **SC-005**: 100% of invalid-input test vectors are rejected explicitly; none produces a successful result.
- **SC-006**: CLI success output parses as one JSON object with exactly the six required keys, and CLI errors return a non-zero status without a JSON success object.

## Assumptions

- Client identifiers are opaque, non-empty strings; the system does not normalize or otherwise reinterpret their content.
- Segment values are case-sensitive and must be exactly `CASH` or `FO`.
- The grace percentage must be non-negative. No maximum is added because none was specified; a percentage above 100 is accepted and the net shortfall formula clamps its result to zero.
- Library callers provide `Decimal` values directly. CLI callers provide decimal text, parsed without passing through binary floating-point.
- The CLI receives one calculation request per invocation using `--client-id`, `--segment`, `--peak-margin-required`, and `--allocated-collateral`, with optional `--grace-limit-pct`.
- Library numeric result fields are `Decimal`. CLI JSON represents decimal-valued fields as strings to preserve exact decimal values across JSON consumers; penalty output always has two fractional digits.
- Intermediate values retain their exact decimal result; only the final penalty amount is rounded to two decimal places.
- The feature calculates one client and segment per invocation. Batch processing, persistence, external integrations, and policy configuration are outside this feature.
