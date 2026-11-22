# Feature Specification: AI Query & Shortfall Explanation Assistant

**Feature Branch**: `001-ai-query-assistant`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Build a Python-based AI Query & Shortfall Explanation Assistant for clearing members using local Ollama (qwen2.5:3b). The assistant must parse natural language member inquiries regarding margin shortfalls or penalties and output a structured JSON response containing: member_code, segment (CASH/FO), shortfall_amount, penalty_slab, explanation, remediation_action, severity, and clarification_required (boolean). Define output schema contracts, structural invariants, guardrail rules (must request clarification if member code or segment is missing), and an evaluation threshold of 85% aggregate score across the evaluation dataset."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explain a Shortfall Inquiry (Priority: P1)

A clearing member asks in natural language about a margin shortfall or penalty. The assistant identifies the member and segment, derives the chargeable shortfall and applicable slab from the supplied information, and returns a concise, grounded explanation and remediation action in the agreed JSON contract.

**Why this priority**: Giving clearing members a consistent and understandable explanation of a shortfall is the primary purpose of the assistant.

**Independent Test**: Submit representative inquiries with unambiguous member, segment, margin, and collateral details. Validate every response against the output contract and independently verify the shortfall and slab.

**Acceptance Scenarios**:

1. **Given** an inquiry that unambiguously supplies a member code, CASH or FO segment, required margin, and allocated collateral, **When** the assistant responds, **Then** it returns all eight required fields, calculates the chargeable shortfall and slab correctly, and grounds its explanation and remediation in those values.
2. **Given** an inquiry with enough details to determine there is no shortfall, **When** the assistant responds, **Then** `shortfall_amount` is `"0"`, `penalty_slab` is `"0.0%"`, and the explanation does not claim that a penalty is due.
3. **Given** the same inquiry and local model configuration, **When** it is evaluated repeatedly, **Then** the structured values and calculation are consistent.

### User Story 2 - Clarify Incomplete or Ambiguous Inquiries (Priority: P1)

A clearing member submits an inquiry without a member code or segment, or without enough financial details to determine the shortfall. The assistant identifies what is missing and asks for it instead of guessing or presenting an unsupported calculation.

**Why this priority**: A guessed identity, segment, or financial value could misdirect an operational response or create a misleading penalty explanation.

**Independent Test**: Submit inquiries missing each required identity, segment, or calculation input and verify `clarification_required`, nullable fields, and the clarification request.

**Acceptance Scenarios**:

1. **Given** an inquiry with no identifiable member code, **When** the assistant responds, **Then** `clarification_required` is `true`, `member_code` is `null`, and the explanation or remediation action asks for the member code.
2. **Given** an inquiry with no identifiable segment, **When** the assistant responds, **Then** `clarification_required` is `true`, `segment` is `null`, and the explanation or remediation action asks whether the segment is CASH or FO.
3. **Given** an inquiry with member and segment but insufficient or conflicting calculation details, **When** a reliable shortfall cannot be established, **Then** the assistant asks for the missing or conflicting details, sets `clarification_required` to `true`, and does not invent a shortfall or slab.

### User Story 3 - Keep Explanations Local and Calculations Grounded (Priority: P1)

A clearing member receives an explanation generated from local processing and validated source values; the assistant does not send an inquiry to a cloud model or let generated text replace the established penalty calculation rules.

**Why this priority**: Margin and penalty explanations must preserve financial correctness and member data confidentiality.

**Independent Test**: Verify the selected model is the configured local model, test boundary cases against the authoritative penalty rules, and inspect outputs for unsupported facts or calculations.

**Acceptance Scenarios**:

1. **Given** a valid inquiry containing financial inputs, **When** a shortfall and slab are returned, **Then** those values agree with the established shortfall and slab rules, including grace where supplied.
2. **Given** model output that is malformed, conflicts with the validated input, or contains unsupported financial values, **When** the assistant processes it, **Then** it does not return the unsupported values as a successful calculation.
3. **Given** any inquiry, **When** it is processed, **Then** the inquiry is handled with the local `qwen2.5:3b` model and is not transmitted to an external model or service.

### User Story 4 - Ask Flexible and Related Questions in the Web App (Priority: P1)

A clearing member asks one or more related questions about a client's short allocation, grace treatment, or penalty slab using their own wording and an informal format. The web assistant answers the supported rule questions and includes a deterministic client calculation when enough client facts are supplied.

**Why this priority**: Members should not have to learn a single sentence template or submit separate requests for related shortfall questions.

**Independent Test**: Submit rule questions, alternate phrasings and a compound question through the web interface. Verify grounded answers, optional calculation behavior, and no fabricated client-specific values when none were supplied.

**Acceptance Scenarios**:

1. **Given** a question about grace and penalty slabs without client values, **When** it is submitted in the web app, **Then** the answer explains both topics and does not fabricate a client calculation.
2. **Given** an inquiry that combines a shortfall calculation and a slab question using prose, bullets, or key-value details, **When** it is submitted, **Then** the answer addresses the related topics and includes the deterministic calculation result.
3. **Given** a question outside the supported shortfall, grace, and penalty-slab topics, **When** it is submitted, **Then** the assistant states its supported scope and does not invent an answer.

### Edge Cases

- Member code or segment is absent, unidentifiable, or ambiguous: request clarification and do not infer it from conversation context not present in the request.
- Segment is supplied in an unambiguous case variant: it may be normalized to the exact contract value `CASH` or `FO`; an unsupported or ambiguous segment requires clarification.
- Required margin or allocated collateral is missing, malformed, negative, non-finite, or conflicting: do not calculate; request clarification or report invalid input without emitting a successful calculation.
- Only a shortfall amount is provided: treat it as the net chargeable shortfall unless the inquiry explicitly identifies it as raw/gross; if an explicitly raw shortfall needs unavailable margin or grace details to derive the net value, ask for those details.
- A stated penalty slab conflicts with the slab derived from the net shortfall: do not repeat it as the applicable slab; explain the discrepancy or ask for clarification.
- Net shortfall is zero: return `"0"` and `"0.0%"`; severity is `LOW`.
- Net shortfall is exactly 100000 INR: the 0.5% slab applies; at 100000.01 INR the 1.0% slab applies.
- Net shortfall is exactly 1000000 INR: the 1.0% slab applies; at 1000000.01 INR the 5.0% slab applies.
- Local model service is unavailable or its output cannot be validated: report an explicit operational failure and do not emit a success-shaped response.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The assistant MUST accept a natural-language inquiry about a member's margin shortfall or penalty and produce a successful response as one JSON object conforming to the response contract below.
- **FR-002**: The assistant MUST use the local Ollama model `qwen2.5:3b` for natural-language interpretation and explanation. Member inquiry content MUST NOT be sent to a cloud model or other external service.
- **FR-003**: The assistant MUST return exactly these eight top-level fields on a successful response: `member_code`, `segment`, `shortfall_amount`, `penalty_slab`, `explanation`, `remediation_action`, `severity`, and `clarification_required`. It MUST NOT add uncontracted fields.
- **FR-004**: `member_code` MUST be a non-empty string when unambiguously identified and otherwise `null`. The assistant MUST NOT fabricate or guess a member code.
- **FR-005**: `segment` MUST be exactly `CASH` or `FO` when unambiguously identified and otherwise `null`. The assistant MUST set `clarification_required` to `true` and ask the member to provide or confirm the segment whenever it is missing or ambiguous.
- **FR-006**: The assistant MUST set `clarification_required` to `true` and request the missing member code whenever no member code is unambiguously available.
- **FR-007**: `shortfall_amount` MUST represent the net, chargeable shortfall in INR as a non-negative, finite base-10 decimal string, with no currency symbol, grouping separator, or exponent notation, or be `null` when it cannot be reliably determined.
- **FR-008**: `penalty_slab` MUST be one of `"0.0%"`, `"0.5%"`, `"1.0%"`, or `"5.0%"`, or `null` when it cannot be reliably determined. Slab selection MUST follow the established rules for net shortfall: zero maps to 0.0%; greater than zero through 100000 INR maps to 0.5%; greater than 100000 through 1000000 INR maps to 1.0%; and greater than 1000000 INR maps to 5.0%.
- **FR-009**: The assistant MUST use validated inquiry values and the established deterministic penalty calculation rules as the sole source of financial results. It MUST NOT use unvalidated model-generated numbers, assumptions, or arithmetic as a shortfall or slab.
- **FR-010**: When required calculation inputs are missing, malformed, non-finite, negative, or contradictory, the assistant MUST NOT invent a shortfall or applicable slab. It MUST ask for clarification when more information can resolve the issue, or return an explicit failure for invalid or unusable input.
- **FR-011**: `explanation` and `remediation_action` MUST be non-empty strings. They MUST be consistent with the identified values, explain any clarification needed, and avoid asserting unsupported member-specific facts, causes, deadlines, or policy.
- **FR-012**: `severity` MUST be one of `"LOW"`, `"MEDIUM"`, `"HIGH"`, or `"UNKNOWN"`. It MUST be `UNKNOWN` while a required value prevents reliable severity assessment. For a determined result, zero or 0.5% slab maps to LOW, 1.0% maps to MEDIUM, and 5.0% maps to HIGH.
- **FR-013**: `clarification_required` MUST be a JSON boolean. It MUST be `true` when the member code, segment, or information required for a reliable requested calculation or explanation is missing or ambiguous; otherwise it MUST be `false`.
- **FR-014**: If `clarification_required` is `true`, unknown member, segment, shortfall, and slab values MUST be `null`; known values MAY be returned. The explanation or remediation action MUST explicitly identify the information requested. If it is `false`, `member_code`, `segment`, `shortfall_amount`, and `penalty_slab` MUST all be non-null.
- **FR-015**: The assistant MUST distinguish a successful response conforming to the eight-field schema from operational failures, including local model unavailability and malformed or unvalidated model output. An operational failure MUST NOT be represented as a successful response or silently replaced by guessed values.
- **FR-016**: Local interpretation and explanation MUST not modify the existing deterministic penalty rules, which use exact decimal arithmetic and the established slab boundaries.
- **FR-017**: The web application MUST accept free-form prose, bullet points, and key-value details without requiring one sentence template. A single inquiry MAY include multiple related questions about shortfall, grace, required calculation inputs, or penalty slabs.
- **FR-018**: For supported rule questions, the web application MUST answer from the calculation and slab rules defined in this specification. It MUST NOT invent client-specific facts or calculate an unprovided total penalty amount.
- **FR-019**: The web API MUST return an object with exactly `answer` and `calculation` fields. `answer` MUST be a non-empty string. `calculation` MUST be `null` when no client-specific facts are supplied, or otherwise contain the eight-field Assistant Response defined below.

### Output Schema Contract

The following schema defines every successful response. Monetary amount values are strings to preserve exact decimal representation. `null` is permitted only where stated by the field contract and structural invariants.

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "member_code",
    "segment",
    "shortfall_amount",
    "penalty_slab",
    "explanation",
    "remediation_action",
    "severity",
    "clarification_required"
  ],
  "properties": {
    "member_code": {
      "type": ["string", "null"],
      "minLength": 1
    },
    "segment": {
      "enum": ["CASH", "FO", null]
    },
    "shortfall_amount": {
      "type": ["string", "null"],
      "pattern": "^(0|[1-9][0-9]*)(\\.[0-9]+)?$"
    },
    "penalty_slab": {
      "enum": ["0.0%", "0.5%", "1.0%", "5.0%", null]
    },
    "explanation": {
      "type": "string",
      "minLength": 1
    },
    "remediation_action": {
      "type": "string",
      "minLength": 1
    },
    "severity": {
      "enum": ["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
    },
    "clarification_required": {
      "type": "boolean"
    }
  }
}
```

### Web Query Response

The browser interface's `/api/query` endpoint returns exactly the following fields. A general rule answer does not require member-specific fields; a client-specific calculation is included only when the inquiry provides client facts.

```json
{
  "answer": "Grace reduces the raw shortfall by peak margin multiplied by the grace limit percentage. The slab depends on the resulting net shortfall.",
  "calculation": null
}
```

When `calculation` is non-null, it MUST conform to the eight-field Assistant Response schema above. The `answer` and calculation MUST agree. The web application continues to process inquiries locally with Ollama and deterministic calculation rules.

### Structural Invariants

- Every successful JSON object contains all eight required fields exactly once and has no additional top-level fields.
- `segment` is either `CASH`, `FO`, or `null`; it is never another string in a successful response.
- When `clarification_required` is `true`, no unknown identity, segment, shortfall, or slab may be fabricated; each unknown is `null`, and the response explicitly asks for the missing information.
- When `clarification_required` is `false`, `member_code`, `segment`, `shortfall_amount`, and `penalty_slab` are all present and non-null.
- A non-null `shortfall_amount` is a non-negative finite decimal string. Its slab is the one selected by the stated boundaries.
- `severity` agrees with the slab mapping, except that an unresolved assessment uses `UNKNOWN`.
- `explanation` and `remediation_action` remain grounded in supplied or validated facts and do not contradict the other fields.
- A successful clarification response still conforms to the same eight-field contract; an operational failure is not a successful response.

### Key Entities

- **Member Inquiry**: A clearing member's natural-language question and any supplied identity, segment, margin, collateral, grace, shortfall, or slab details.
- **Assistant Response**: The eight-field JSON result containing extracted identity and segment, a validated chargeable shortfall and slab when determinable, an explanation, a remediation action, a severity, and a clarification flag.
- **Evaluation Case**: A representative inquiry with expected extracted values, calculation outcome, clarification behavior, and response-contract assertions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The assistant achieves an aggregate score of at least 85% across the designated evaluation dataset. The aggregate score is the mean case score; each case is scored out of 100 using: response schema and invariants (20 points), extraction of identity/segment/financial facts (25 points), shortfall and slab correctness (25 points), grounded explanation and remediation (15 points), and clarification behavior (15 points).
- **SC-002**: 100% of evaluation cases with a missing or ambiguous member code or segment set `clarification_required` to `true`, explicitly request the missing information, and do not invent the missing value.
- **SC-003**: 100% of successful responses parse as JSON and satisfy the required field set, field types, allowed values, and structural invariants.
- **SC-004**: 100% of evaluation cases with enough financial input to calculate a result return a shortfall and slab matching the deterministic rules, including all specified slab boundaries.
- **SC-005**: 0 evaluation responses assert unsupported financial amounts, member-specific causes, remediation deadlines, or policy facts as established facts.
- **SC-006**: At least 85% of evaluation responses are rated understandable and actionable by reviewers familiar with clearing-member operations.
- **SC-007**: 100% of inquiry processing keeps inquiry content within the local environment and sends no member information to an external model or service.

## Assumptions

- The existing short-allocation penalty rules are authoritative for calculating the net chargeable shortfall and its slab; the assistant interprets and explains inquiries but does not create or alter those rules.
- `shortfall_amount` means net, chargeable shortfall after any applicable grace treatment. If an inquiry supplies only a shortfall amount without identifying it as raw/gross, it is treated as net; an explicitly raw amount that cannot be converted to net without missing inputs requires clarification.
- `penalty_slab` is the applicable penalty percentage, serialized with a percent sign in one of the four enumerated values.
- Severity is a user-facing shortfall classification derived from the applicable slab: zero and 0.5% are LOW, 1.0% is MEDIUM, and 5.0% is HIGH. It is not a separate regulatory or credit-risk rating.
- A successful response is the eight-field JSON object. If local inference or response validation fails, the invocation reports an explicit operational failure rather than fabricating a schema-valid answer.
- Inquiry content and model processing remain local; no member database, persistent conversation history, cloud inference, or external data source is implied.
- The evaluation dataset includes complete, boundary, incomplete, ambiguous, malformed, and contradictory inquiries, with expected outputs reviewed against the response contract and established calculation rules.
- Reviewers familiar with clearing-member operations assess whether explanations are understandable and remediation actions are actionable.
- This feature adds a local natural-language assistant without changing the existing calculator's established behavior or penalty thresholds.
