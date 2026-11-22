# Implementation Plan: Client Short Allocation & Penalty Calculation

**Branch**: `001-short-allocation-penalty` | **Date**: 2026-11-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-short-allocation-penalty/spec.md`

## Summary

Implement a stateless, deterministic library calculation and a one-request-per-invocation CLI for clearing short allocation penalties. Validate all request values before calculation, use `Decimal` without intermediate rounding, apply the specified shortfall slabs, and round only the final penalty to two places using `ROUND_HALF_UP`. The CLI accepts the specified named flags and emits one JSON object with decimal values represented as strings.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: Python standard library for runtime; `pytest` for tests. `ruff` and `bandit` are required development/CI gates, not runtime dependencies.

**Storage**: N/A; calculations are stateless and no client data is persisted.

**Testing**: `pytest` unit and CLI contract tests; `ruff` linting; `bandit` security analysis.

**Target Platform**: Any operating system with Python 3.10 or later.

**Project Type**: Reusable Python library and command-line interface.

**Performance Goals**: No latency or throughput target is specified. The supported scope is one client calculation per invocation.

**Constraints**: Exact decimal arithmetic for all INR values; no binary floating-point conversions, random behavior, external API calls, runtime dependencies outside the standard library, or intermediate rounding. Validate finite Decimal inputs and report invalid inputs explicitly.

**Scale/Scope**: One client and one segment per library call or CLI invocation. Batch processing, persistence, integrations, and policy configuration are out of scope.

## Constitution Check

| Gate | Plan decision | Status |
|---|---|---|
| Deterministic calculations | Pure calculation operation; no random or time-dependent inputs and no external API calls. | PASS |
| Exact INR arithmetic | Decimal inputs and outputs; no float conversions; only final penalty quantized with `ROUND_HALF_UP`. | PASS |
| Strict input contracts | Validate identifiers, segment, Decimal type/finiteness, and non-negative numeric constraints; use a custom validation exception. | PASS |
| Testable design | Keep calculation logic separate from CLI argument parsing/serialization; cover behavior with unit and contract tests. | PASS |
| Dependency/security limits | Standard library at runtime; pytest for tests; no secrets or unnecessary dependencies. | PASS |
| Quality gates | Run ruff, bandit, and pytest with zero errors. | PASS |

No constitution violations are identified. The specified Decimal string representation at the CLI boundary preserves values without introducing float conversion.

## Project Structure

### Documentation (this feature)

```text
specs/001-short-allocation-penalty/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── interfaces.md
```

### Source Code (repository root)

```text
.gitignore
pyproject.toml

client_short_allocation/
├── __init__.py
├── calculator.py
└── cli.py

tests/
├── unit/
│   ├── __init__.py
│   └── test_calculator.py
└── contract/
    ├── __init__.py
    └── test_cli.py
```

**Structure Decision**: Use a small root-level package so the library is importable without adding packaging/build dependencies or requiring an installation step. Keep the public calculation interface in the package, its domain validation and math in `calculator.py`, and command-line parsing/JSON serialization in `cli.py`. Use separate unit and CLI contract tests. This is a new application layout; no existing source code or test structure was present in the feature project.

**Post-design Constitution Check**: PASS. The library/CLI separation adds no runtime dependency or external service. Decimal arithmetic, validation, determinism, and the required pytest/ruff/bandit gates remain aligned with the constitution.

## Phase 0: Outline & Research

The specification and constitution settle the language, runtime dependencies, arithmetic model, input/output behavior, and test gates. There are no unresolved technical choices requiring additional research. See [research.md](./research.md) for the decisions and rejected alternatives.

## Phase 1: Design & Contracts

- [Data model](./data-model.md) defines request/result fields and validation rules.
- [Interface contracts](./contracts/interfaces.md) define the library and CLI boundaries, error behavior, and JSON shape.
- [Quickstart](./quickstart.md) defines reproducible validation steps and expected output.

## Complexity Tracking

No constitution violations or additional architectural complexity are introduced.
