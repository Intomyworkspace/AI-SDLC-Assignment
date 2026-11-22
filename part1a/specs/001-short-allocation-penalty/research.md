# Research: Client Short Allocation & Penalty Calculation

## Decision: Standard-library Python package

- **Decision**: Implement for Python 3.10+ using only the standard library at runtime; use `pytest` for tests.
- **Rationale**: These are explicit project constitution constraints. The repository has no existing application/package structure, so a root-level package avoids adding a build backend or runtime dependencies.
- **Alternatives considered**: A third-party CLI framework or a `src/` layout with a packaging tool. Both add setup/dependency complexity that is unnecessary for the stated scope and conflicts with the dependency constraints.

## Decision: Separate calculation from the CLI adapter

- **Decision**: Keep validation and penalty math in a reusable library operation and keep flag parsing and JSON serialization in a thin CLI module.
- **Rationale**: The library can be unit-tested directly; CLI behavior can be verified independently as a public contract. Neither layer requires storage or external services.
- **Alternatives considered**: Putting calculation logic directly in the command entry point would make library reuse and independent testing harder.

## Decision: Decimal arithmetic with final-only rounding

- **Decision**: Accept `Decimal` values in the library, parse CLI decimal text directly as `Decimal`, preserve intermediate shortfall/grace values, and quantize only the final penalty with `ROUND_HALF_UP`.
- **Rationale**: This follows the feature requirements and constitution's exact-INR rule. JSON represents Decimal values as strings to preserve exactness for consumers that otherwise parse JSON numbers as binary floats.
- **Alternatives considered**: Binary floating-point and JSON numeric values are excluded because they can lose decimal precision. Rounding intermediate values is excluded because the specified formula only rounds the final penalty.
- **Precision handling**: Use a scoped Decimal context with precision sufficient for the input coefficients and exponent alignment so finite intermediate values are not rounded by a default context. Do not quantize intermediate values; quantize only the final penalty.

## Decision: One calculation per invocation

- **Decision**: The CLI accepts the five specified named flags (grace optional) for one calculation and emits one result object.
- **Rationale**: The CLI input mode and one-client scope are specified. The command needs no service, persistence, or batch-processing layer.
- **Alternatives considered**: JSON input streams, input files, batches, or remote integrations are outside the agreed scope.

## Research status

There are no unresolved technical clarifications. Domain formulas, slab boundaries, input constraints, output keys, CLI flag names, and rounding behavior are defined by the feature specification. No external API or external research source is required.
