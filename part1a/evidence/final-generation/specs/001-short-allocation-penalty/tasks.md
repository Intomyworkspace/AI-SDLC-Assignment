# Tasks: Client Short Allocation & Penalty Calculation

**Input**: Design documents from `specs/001-short-allocation-penalty/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Unit and CLI contract tests are required by the feature specification and project constitution. Write each focused test task before its corresponding implementation task.

**Organization**: Tasks are grouped by user story and ordered by priority. The calculator is a dependency of validation and CLI stories.

## Phase 1: Setup

**Purpose**: Establish the minimal Python package and test/tool configuration.

- [X] T001 Create package and test scaffolding in `client_short_allocation/__init__.py`, `tests/unit/__init__.py`, and `tests/contract/__init__.py`.
- [X] T002 [P] Configure pytest test discovery and Ruff's Python 3.10 target in `pyproject.toml` without adding runtime dependencies.

## Phase 2: Foundational

**Purpose**: Establish the shared public library contract used by all user stories.

- [X] T003 Add the `calculate_penalty` public function signature and `InvalidCalculationInput` exception in `client_short_allocation/calculator.py`, then export both from `client_short_allocation/__init__.py`.

**Checkpoint**: Package and shared library interface are ready for story-level tests and implementation.

## Phase 3: User Story 1 - Calculate a Client Penalty (Priority: P1) — MVP

**Goal**: Calculate raw/net shortfalls, select the correct slab, and return the final rounded penalty for valid input.

**Independent Test**: Run `pytest tests/unit/test_calculator.py`; valid calculation vectors return the six specified fields with exact Decimal values.

### Tests

- [X] T004 [US1] Add unit tests in `tests/unit/test_calculator.py` for zero and grace-default behavior, all slab boundaries (100000, 100000.01, 1000000, 1000000.01 INR), exact intermediate calculations, and ROUND_HALF_UP tie rounding.

### Implementation

- [X] T005 [US1] Implement `calculate_penalty` in `client_short_allocation/calculator.py` using exact Decimal calculations and a scoped precision sufficient to avoid intermediate context rounding; apply the specified slab rates and quantize only the final penalty with `ROUND_HALF_UP` to INR 0.01.

**Checkpoint**: User Story 1 works independently for valid inputs.

## Phase 4: User Story 3 - Reject Invalid Calculation Inputs (Priority: P1)

**Goal**: Reject invalid library requests explicitly without returning a calculation result.

**Independent Test**: Run `pytest tests/unit/test_validation.py`; each invalid library input raises `InvalidCalculationInput` identifying the field.

### Tests

- [X] T006 [US3] Add validation tests in `tests/unit/test_validation.py` for empty/whitespace client IDs, unsupported segments, negative values, non-Decimal numeric types, and non-finite Decimals for all numeric inputs.

### Implementation

- [X] T007 [US3] Enforce request validation in `client_short_allocation/calculator.py`: require a non-whitespace string client ID, exact `CASH`/`FO` segment, finite Decimal numeric inputs, and non-negative margin, collateral, and grace; raise `InvalidCalculationInput` with the field name.

**Checkpoint**: User Stories 1 and 3 work for valid and invalid library inputs.

## Phase 5: User Story 2 - Run the Calculation from the CLI (Priority: P2)

**Goal**: Accept one request through named flags and emit the specified exact JSON result or a clear error.

**Independent Test**: Run `pytest tests/contract/test_cli.py`; successful invocations emit exactly one six-key JSON object with decimal strings, while invalid invocations exit non-zero, write a field-specific error to stderr, and emit no success object.

### Tests

- [X] T008 [P] [US2] Add CLI contract tests in `tests/contract/test_cli.py` for required/optional flags, exact output keys and decimal strings, the representative grace calculation, repeated-input determinism, and malformed/out-of-domain inputs.

### Implementation

- [X] T009 [US2] Implement the CLI in `client_short_allocation/cli.py` with the specified named flags, direct Decimal parsing, JSON string serialization, and non-zero field-specific error handling without a success result on failure.

**Checkpoint**: All three user stories are independently verifiable through the library or CLI contract.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete feature against project quality gates and operational examples.

- [X] T010 Run pytest, Ruff, Bandit, and the representative command in `specs/001-short-allocation-penalty/quickstart.md`; fix any failures in `client_short_allocation/` or `tests/`.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001 and T002 may run in parallel.
- **Foundational (Phase 2)**: T003 depends on package scaffolding in T001 and blocks all user-story work.
- **User Story 1 (Phase 3)**: Depends on T003; T005 follows the test task T004.
- **User Story 3 (Phase 4)**: Depends on the calculation implementation in T005; T007 follows validation tests in T006.
- **User Story 2 (Phase 5)**: The CLI contract test T008 can be authored after T005 and in parallel with T006 because it uses a separate test file. CLI implementation T009 depends on T007 and T008.
- **Polish (Phase 6)**: T010 depends on all desired stories being implemented.

### User Story Dependencies

- **US1 (P1)**: Depends only on Setup and Foundational; MVP for valid calculations.
- **US3 (P1)**: Depends on US1's calculation function; adds comprehensive library input validation.
- **US2 (P2)**: Depends on US1 for calculation and US3 for the library validation error contract used by CLI error handling.

### Parallel Opportunities

- T001 and T002 can run in parallel because they modify different files.
- After T005, T006 and T008 can be authored in parallel because they modify separate test files and exercise distinct interfaces.
- No implementation tasks modify the same source file concurrently; complete T007 before T009.

## Parallel Example

```text
After T005:
Task: T006 — add library validation cases in tests/unit/test_validation.py
Task: T008 — add CLI contract cases in tests/contract/test_cli.py
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Setup and Foundational phases.
2. Add the valid-input calculation tests and implement the Decimal calculation.
3. Validate User Story 1 independently with its focused pytest file.

### Incremental Delivery

1. Add comprehensive library validation as User Story 3.
2. Add the CLI contract and adapter as User Story 2.
3. Run all pytest, Ruff, and Bandit gates and follow the end-to-end quickstart.

## Notes

- Every task uses the required checkbox, sequential ID, optional parallel marker, story label where applicable, and a concrete file path.
- Tests precede their associated implementation tasks.
- No persistence, external integrations, or runtime dependencies are introduced.
