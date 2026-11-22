# Research: AI Query & Shortfall Explanation Assistant

## Decision 1: Keep all inference local

**Decision**: Use the locally running Ollama service with model `qwen2.5:3b`. The application connects only to a loopback Ollama endpoint and does not use a hosted inference provider.

**Rationale**: This meets the model requirement and keeps member inquiries within the local environment. A standard-library HTTP client avoids adding a Python runtime dependency.

**Alternatives considered**:

- Hosted model API: rejected because the specification prohibits sending member information to external services.
- Adding a third-party Python Ollama client: rejected to preserve the standard-library runtime constraint.

## Decision 2: Separate extraction, calculation, and response validation

**Decision**: Treat model output as untrusted extracted data. Normalize and validate its fields, calculate financial results with deterministic `Decimal` logic, then validate the final JSON response against the feature contract. The model is not called from calculation or validation code.

**Rationale**: Language models can omit, misread, or invent values. A pure calculation path and explicit response invariants prevent model-generated arithmetic from appearing authoritative.

**Alternatives considered**:

- Ask the model to calculate shortfall and slab: rejected because it cannot guarantee exact arithmetic or correct boundary selection.
- Infer missing member or segment values from likely context: rejected because the specification requires clarification instead of guessing.

## Decision 3: Use a one-query CLI and JSON response

**Decision**: Accept one natural-language query per command invocation and write one successful response object as JSON to standard output. Report operational failures explicitly without returning a success-shaped response.

**Rationale**: A local CLI is the smallest usable interface consistent with the Python assistant and structured JSON requirement. It is straightforward to test and does not imply a web service or persistent session.

**Alternatives considered**:

- Web service or user interface: deferred because neither is required by the specification.
- Batch request/response interface: deferred; the evaluation dataset is a validation mechanism, not a production batch feature.

## Decision 4: Resolve facts by evidence and deterministic rules

**Decision**: Use only values explicitly supplied or unambiguously stated in the current inquiry. If the member code or segment is missing or ambiguous, return a clarification response. For financial amounts, use the existing stated calculation semantics: exact decimal values, net shortfall after grace when margin and collateral are supplied, and the established slab boundaries.

**Rationale**: No member database or external lookup is in scope. This avoids implying access to account data the assistant does not have.

**Alternatives considered**:

- Add a member or margin data source: rejected as out of scope and not specified.
- Treat an explicitly gross/raw shortfall as net: rejected because it could select an incorrect slab when grace applies; request the inputs needed to derive net shortfall.

## Decision 5: Score the evaluation set using the specified weighted rubric

**Decision**: Score each case on schema/invariants (20), extraction (25), calculation/slab (25), grounded explanation/remediation (15), and clarification behavior (15); report the mean across cases. Separately enforce 100% missing-identity/segment clarification, response-schema compliance, and deterministic calculation correctness requirements.

**Rationale**: This implements the 85% aggregate score while keeping critical correctness and clarification guardrails from being masked by the average.

**Alternatives considered**:

- Single unweighted pass/fail score per case: rejected because it does not reflect the specified aggregate evaluation dimensions.
- Let a high aggregate score compensate for any missing-member or missing-segment guardrail violation: rejected because those conditions require clarification every time.

## Remaining Assumptions

- The local Ollama service is installed, running, and has `qwen2.5:3b` available before the assistant is invoked.
- No production member database, identity provider, or policy source is available to this feature.
- Inquiry and evaluation examples are synthetic or sanitized; actual member data is not committed to the repository.
- Severity remains the specification's user-facing mapping from applicable slab, not an independent regulatory rating.
