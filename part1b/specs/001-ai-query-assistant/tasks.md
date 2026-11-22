# Tasks: AI Query & Shortfall Explanation Assistant

**Input**: Design documents from `specs/001-ai-query-assistant/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/interfaces.md](./contracts/interfaces.md)

**Tests**: Included because the specification requires contract validation, evaluation-dataset scoring, and exact calculation/clarification guardrails.

**Organization**: Tasks are grouped by user story. Complete shared setup and foundational tasks before beginning story work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Tasks touching independent files that can proceed in parallel.
- **[Story]**: User-story label mapping to `spec.md`.
- Every task includes its exact `part1b/` file path.

## Phase 1: Setup

**Purpose**: Establish a standalone Python project and the directory structure described in `plan.md`.

- [ ] T001 Configure Python 3.10+ project metadata, standard-library runtime policy, pytest/ruff settings, and development tool configuration in `part1b/pyproject.toml`.
- [ ] T002 [P] Create the package entry points in `part1b/src/ai_query_assistant/__init__.py` and `part1b/src/ai_query_assistant/__main__.py`, plus the `part1b/tests/unit/`, `part1b/tests/contract/`, `part1b/tests/integration/`, `part1b/evals/`, and `part1b/evaluation/` directories.

## Phase 2: Foundational

**Purpose**: Establish shared typed facts, response validation, and synthetic evaluation inputs required by all stories.

- [ ] T003 [P] Define inquiry, extracted-fact, and calculation-result types in `part1b/src/ai_query_assistant/models.py`; enforce these data-model constraints verbatim: `member_code` is “Non-empty if identified; never guessed”; `segment` follows “Only these values are accepted; ambiguous or missing values require clarification”; margin, collateral, and grace values are “Finite and non-negative when present”; grace “defaults to exact zero only when the inquiry's calculation semantics allow the default”; a direct shortfall follows “an explicitly raw/gross value is not treated as net”; and evidence must “Identify the source portion of the inquiry for each extracted value; do not add facts not found in the inquiry.”
- [ ] T004 [P] Implement the common response-contract validator in `part1b/src/ai_query_assistant/response_validator.py`; enforce exactly the eight required fields and no additional properties. Apply each data-model nullability rule verbatim: `member_code` and `segment` are “null if unknown or clarification is required”; `shortfall_amount` and `penalty_slab` each are “null if it cannot be reliably determined”; `explanation` is “Never null; asks for missing information when needed”; `remediation_action` is “Never null; may request clarification”; severity is “UNKNOWN when it cannot be reliably assessed”; and clarification is “True when identity, segment, or required calculation information is missing or ambiguous.” Also enforce the cross-field invariants from `part1b/specs/001-ai-query-assistant/spec.md`.
- [ ] T005 [P] Create exactly 15 synthetic, non-sensitive test cases in `part1b/evals/dataset.json` covering normal inquiries, grace boundaries, slab boundaries, ambiguous complaints, missing member codes, missing segments, malformed values, negative values, and adversarial/guardrail behavior; include expected structured fields and semantic text assertions.

**Checkpoint**: Shared data types, response validation, and synthetic evaluation cases are available before story implementation.

## Phase 3: User Story 1 - Explain a Shortfall Inquiry (Priority: P1) 🎯 MVP

**Goal**: Accept a complete, unambiguous inquiry and return a grounded explanation with the correctly calculated net shortfall and slab.

**Independent Test**: With Ollama replaced by a deterministic local fake, submit a complete inquiry and verify all eight JSON fields; independently check Decimal shortfall, slab, and severity results, including a zero-shortfall case.

### Tests for User Story 1

- [ ] T006 [P] [US1] Add unit tests for exact Decimal shortfall, grace, slab boundaries, and severity in `part1b/tests/unit/test_calculator.py`; include net shortfalls of 0, 100000, 100000.01, 1000000, and 1000000.01 INR.
- [ ] T007 [P] [US1] Add mocked-Ollama integration tests for complete natural-language inquiries and a no-shortfall inquiry in `part1b/tests/integration/test_inquiry_pipeline.py`.
- [ ] T008 [P] [US1] Add successful-response contract tests for exactly eight fields, valid types and enums, decimal strings, and no extra properties in `part1b/tests/contract/test_response_contract.py`.

### Implementation for User Story 1

- [X] T009 [P] [US1] Implement a standard-library client for local Ollama inference using only model `qwen2.5:3b` in `part1b/src/assistant.py`; return evidence-backed candidate extracted facts and explanation text without calculating financial results.
- [ ] T010 [US1] Implement natural-language fact extraction and normalization in `part1b/src/ai_query_assistant/inquiry_parser.py`; “Identify the source portion of the inquiry for each extracted value; do not add facts not found in the inquiry,” use only facts explicitly supplied or unambiguously stated in the current query, and convert decimal text directly to `Decimal`.
- [ ] T011 [P] [US1] Implement pure exact-Decimal calculation in `part1b/src/ai_query_assistant/calculator.py`; calculate raw shortfall as `max(0, peak_margin_required - allocated_collateral)`, allowable grace as `peak_margin_required * (grace_limit_pct / 100)`, and net shortfall as `max(0, raw_shortfall - allowable_grace)`. Select 0.0% at zero, 0.5% for `(0, 100000]`, 1.0% for `(100000, 1000000]`, and 5.0% above 1000000 INR; map zero/0.5% to LOW, 1.0% to MEDIUM, and 5.0% to HIGH. Use `Decimal`, with no I/O, binary floats, or model calls.
- [X] T012 [US1] Implement response construction in `part1b/src/prediction_generator.py`; combine evidence-validated facts and deterministic calculation results with a grounded explanation and remediation action.
- [X] T013 [US1] Implement the one-query CLI and JSON output in `part1b/src/cli.py`; require `--query`, emit one successful response object only, and report operational failures without emitting a success-shaped response.

**Checkpoint**: User Story 1 works independently with a fake local model and passes focused unit, integration, and contract tests.

## Phase 4: User Story 2 - Clarify Incomplete or Ambiguous Inquiries (Priority: P1)

**Goal**: Request missing member, segment, or calculation information instead of guessing or returning unsupported financial values.

**Independent Test**: Submit queries missing each required identity, segment, or calculation input; verify `clarification_required` is `true`, unknown values are null, and the response explicitly asks for the missing information.

### Tests for User Story 2

- [ ] T014 [P] [US2] Add contract tests for missing/ambiguous member code and segment, asserting clarification is mandatory and unknown response fields are null in `part1b/tests/contract/test_clarification.py`.
- [ ] T015 [P] [US2] Add parser tests for incomplete, malformed, negative, non-finite, and contradictory financial values in `part1b/tests/unit/test_inquiry_parser.py`.

### Implementation for User Story 2

- [ ] T016 [US2] Implement clarification decisions in `part1b/src/ai_query_assistant/response_builder.py`; set `clarification_required` to true for missing/ambiguous member code, segment, or required calculation facts, preserve only known values, and explicitly ask for each missing item.
- [ ] T017 [US2] Update `part1b/src/ai_query_assistant/inquiry_parser.py` to reject or mark unknown malformed and contradictory facts; never infer member code, segment, or financial values from unstated context.

**Checkpoint**: User Story 2 passes independently for missing identity, missing segment, and insufficient or conflicting financial information.

## Phase 5: User Story 3 - Keep Explanations Local and Calculations Grounded (Priority: P1)

**Goal**: Keep inquiry processing local and ensure generated text cannot override validated input or deterministic financial results.

**Independent Test**: Use a fake Ollama response containing incorrect monetary values, an invalid segment, and unsupported claims; verify that no unsupported values appear in a successful response. Simulate Ollama unavailability and verify an explicit operational failure.

### Tests for User Story 3

- [X] T018 [P] [US3] Add tests for Ollama unavailability, malformed model output, unexpected model identity, and absence of remote fallback in `part1b/tests/test_assistant.py`.
- [X] T019 [P] [US3] Add tests proving malformed or unsupported model results do not pass evaluation invariants in `part1b/tests/test_eval_runner.py`.

### Implementation for User Story 3

- [X] T020 [US3] Restrict transport in `part1b/src/assistant.py` to the local Ollama endpoint; add bounded timeouts and explicit transport/response errors, with no cloud or remote fallback and no persistence of inquiry text.
- [ ] T021 [US3] Enforce trusted-value precedence in `part1b/src/ai_query_assistant/response_builder.py` and `part1b/src/ai_query_assistant/response_validator.py`; derive financial fields only from validated input and calculator output, and reject malformed or unsupported model claims rather than returning them as success.

**Checkpoint**: User Story 3 passes locality, invalid-model-output, calculation-isolation, and explicit-failure tests.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Measure the specified aggregate evaluation target and validate the complete feature.

- [X] T022 Add evaluation-runner tests in `part1b/tests/test_eval_runner.py`; verify weighted scoring, the 85% understandable/actionable reviewer threshold, and separate 100% missing-identity/segment clarification, response-schema, and calculation-correctness guardrails.
- [X] T023 Implement the three-layer evaluation runner in `part1b/.harness/eval_runner.py`; read `part1b/evals/dataset.json`, compute the mean case score using the specified weights: schema/invariants 20, extraction 25, calculation/slab 25, grounded explanation/remediation 15, and clarification behavior 15, and report the percentage of responses reviewer-rated understandable and actionable.
- [X] T024 [P] Update `part1b/specs/001-ai-query-assistant/quickstart.md` with the implemented module usage, local Ollama prerequisites, test commands, evaluation invocation, and expected results.
- [ ] T025 From `part1b/`, run `python -m unittest discover -s tests`, `ruff check src tests .harness`, `bandit -r src .harness`, and `python .harness/eval_runner.py`; fix failures and confirm an aggregate score of at least 85%, at least 85% understandable/actionable reviewer ratings, and all independent guardrails. Evaluation code: `part1b/.harness/eval_runner.py`.
- [X] T026 Implement `part1b/src/prediction_generator.py` and `part1b/.harness/generate_predictions.py` to generate responses only from local Ollama-extracted candidate facts and deterministic calculation rules, without reading expected labels.
- [X] T027 Update `part1b/.harness/eval_runner.py` to generate a missing predictions file and represent human-review ratings as pending until reviewers provide them.

## Dependencies & Execution Order

### Phase Dependencies

- **Execution graph**: `Phase 1 Setup → Phase 2 Foundation → US1 → US2 → US3 → Phase 6 Polish`.
- **Setup (Phase 1)**: No dependencies; establishes project metadata and skeleton.
- **Foundational (Phase 2)**: Depends on Setup; blocks user story work.
- **User Story 1 (Phase 3)**: Depends on Foundation; establishes the complete-inquiry MVP.
- **User Story 2 (Phase 4)**: Depends on Foundation and the response pipeline from US1; adds safe clarification behavior.
- **User Story 3 (Phase 5)**: Depends on the local inference and response pipeline from US1 and clarification behavior from US2; hardens locality and financial trust boundaries.
- **Polish (Phase 6)**: Depends on all user stories; evaluates and validates the complete assistant.

### User Story Dependencies

- **US1 (P1)**: Can start after Foundation; first independently testable assistant capability and MVP.
- **US2 (P1)**: Extends US1's query and response pipeline; its clarification behavior is tested independently.
- **US3 (P1)**: Verifies and hardens the shared inference/calculation boundary after the pipeline is present.

### Within Each User Story

- Write and run the story's focused tests before implementation; confirm they fail for the missing behavior.
- Keep calculation pure and independent from Ollama communication.
- Build response construction after parser and calculator results are available.
- Complete each story checkpoint before proceeding to the next story.

### Parallel Opportunities

- Setup: T001 and T002 operate on separate files.
- Foundation: T003, T004, and T005 operate on separate files and can proceed in parallel after the skeleton exists.
- US1 tests: T006, T007, and T008 use separate test files and can be authored in parallel; T009 and T011 can also proceed in parallel after those tests and foundation.
- US2 tests: T014 and T015 use separate files and can proceed in parallel.
- US3 tests: T018 and T019 use separate files and can proceed in parallel.
- Polish: T024 can proceed independently of evaluation code and tests.

### Parallel Example: User Story 1

```text
Task T006: Add calculator boundary tests in part1b/tests/unit/test_calculator.py
Task T007: Add mocked inquiry pipeline tests in part1b/tests/integration/test_inquiry_pipeline.py
Task T008: Add response contract tests in part1b/tests/contract/test_response_contract.py
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Setup and Foundation.
2. Complete US1 tests and implementation.
3. Validate complete inquiries and deterministic calculation results with a fake Ollama boundary.
4. **Stop and validate**: the first increment can answer complete, unambiguous queries with a valid JSON response.

### Incremental Delivery

1. Add US2 clarification behavior and verify all missing/ambiguous-input guardrails.
2. Add US3 locality, failure, and model/calculation isolation controls.
3. Add the weighted evaluation runner, run all quality gates, and confirm the aggregate threshold and hard guardrails.

## Notes

- Every task follows the required `- [ ] T### [P?] [US?] ... file path` format.
- `[P]` appears only where tasks operate on independent files and have no unfinished task dependency.
- The evaluation dataset must use synthetic or sanitized inquiries; do not commit real member information.
