# Implementation Plan: AI Query & Shortfall Explanation Assistant

**Branch**: `not specified` | **Date**: 2026-11-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-ai-query-assistant/spec.md`

## Summary

Build a local Python assistant that interprets one member inquiry at a time with Ollama's `qwen2.5:3b`, validates extracted facts, calculates shortfall and slab using deterministic exact-decimal rules, and returns the specified eight-field JSON response. Keep model communication isolated from calculation and validation so generated financial claims are never authoritative.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: Python standard library at runtime; locally installed Ollama with `qwen2.5:3b`; `pytest` for tests. No Python runtime package is required for the local Ollama connection.

**Storage**: None. Do not retain inquiries or response history.

**Testing**: `pytest` unit, contract, and mocked-Ollama integration tests; evaluation against the designated synthetic dataset; `ruff` and `bandit` quality gates.

**Target Platform**: Operating systems supported by Python 3.10+ and Ollama.

**Project Type**: Local command-line assistant and loopback-only browser interface, one inquiry per request.

**Performance Goals**: No response-time service-level objective is specified. The local model's inference time is expected to dominate; the application must not hang indefinitely if Ollama is unavailable.

**Constraints**: Use only local Ollama inference; expose the browser interface only on loopback; validate the model response against a strict structured contract; use `Decimal` for INR amounts; no model calls from calculation or validation logic; no unsupported external data or member lookup; no persistence of inquiry content.

**Scale/Scope**: Single inquiry and response per invocation or web request; a web inquiry may contain multiple related shortfall, grace, or penalty-slab questions. Batch evaluation is for development validation only. Member databases, remote services, authentication, and long-term conversation memory are out of scope.

## Constitution Check

Part 1b has no local constitution file. The following gates apply the feature requirements and the related calculation principles already established for this project:

| Gate | Plan decision | Status |
|---|---|---|
| Local processing and confidentiality | Send inquiry text only to the local Ollama service; do not transmit it to external services or retain it. | PASS |
| Deterministic exact-decimal calculations | Keep financial calculations in a pure component using `Decimal`; model output cannot set or override a calculated shortfall or slab. | PASS |
| Strict contracts and guardrails | Validate extracted facts and final JSON; missing member code or segment always requires clarification. | PASS |
| Testable separation | Keep CLI, Ollama communication, extraction normalization, calculation, and response validation independently testable. | PASS |
| Runtime dependency limits | Use the standard library for application code and local HTTP communication; keep `pytest`, `ruff`, and `bandit` as development tools. | PASS |
| Explicit failure handling | Ollama unavailability, malformed output, and invalid input produce explicit failures or clarification responses, never a fabricated success. | PASS |

The local model is used only for inquiry interpretation and explanation. It is not called from financial calculation or input validation paths.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-query-assistant/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── interfaces.md
└── spec.md
```

### Source Code (part1b)

```text
src/
├── assistant.py
├── cli.py
├── prediction_generator.py
└── ai_query_assistant/
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    ├── inquiry_parser.py
    ├── models.py
    ├── calculator.py
    ├── response_builder.py
    └── response_validator.py

tests/
├── unit/
├── contract/
├── integration/
├── test_assistant.py
└── test_eval_runner.py

evals/
└── dataset.json

.harness/
├── eval_runner.py
└── generate_predictions.py
```

**Structure Decision**: Keep the application and harness in `part1b`. `src/assistant.py` owns the local Ollama connection and evidence-backed candidate extraction; `src/prediction_generator.py` derives exact-decimal results and assembles contract responses without reading expected labels; `src/cli.py` exposes one-query JSON output. `.harness/eval_runner.py` runs structural, invariant, and semantic evaluation layers and generates a missing predictions file locally; `.harness/generate_predictions.py` can also generate that file directly. Keep tests and the synthetic evaluation dataset within `part1b`; do not import application code from or modify `part1a`.

## Phase 0: Outline & Research

The feature spec fixes the model, output fields, missing-information behavior, evaluation target, and calculation authority. [research.md](./research.md) records the remaining design choices and assumptions: local Ollama transport, interface shape, fact precedence, and evaluation methodology.

## Phase 1: Design & Contracts

- [Data model](./data-model.md) defines inquiry facts, calculation values, and the response invariants.
- [Interface contracts](./contracts/interfaces.md) define the local CLI boundary, Ollama boundary, error behavior, and response contract reference.
- [Quickstart](./quickstart.md) defines local prerequisites and representative validation scenarios.

**Post-design Constitution Check**: PASS. The model boundary remains local and isolated. All financial arithmetic and validation are deterministic and exact-decimal; no code or artifacts in `part1a` need to change.

## Complexity Tracking

No constitution violations or additional architectural complexity are introduced.
