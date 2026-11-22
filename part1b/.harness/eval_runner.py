"""Three-layer evaluation runner for the AI Query Assistant."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from assistant import OllamaClient

RESPONSE_FIELDS = {
    "member_code",
    "segment",
    "shortfall_amount",
    "penalty_slab",
    "explanation",
    "remediation_action",
    "severity",
    "clarification_required",
}
DECIMAL_PATTERN = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")


def _decimal(value: Any) -> Decimal | None:
    if not isinstance(value, str) or not DECIMAL_PATTERN.fullmatch(value):
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number.is_finite() and number >= 0 else None


def _slab_for(amount: Decimal) -> str:
    if amount == 0:
        return "0.0%"
    if amount <= Decimal(100000):
        return "0.5%"
    if amount <= Decimal(1000000):
        return "1.0%"
    return "5.0%"


def _severity_for(slab: str) -> str:
    return {
        "0.0%": "LOW",
        "0.5%": "LOW",
        "1.0%": "MEDIUM",
        "5.0%": "HIGH",
    }.get(slab, "UNKNOWN")


def layer1_structural(response: Any) -> dict[str, Any]:
    """Validate the exact response schema, field types, and allowed values."""
    errors: list[str] = []

    if not isinstance(response, dict):
        return {"passed": False, "errors": ["response must be a JSON object"]}

    if set(response) != RESPONSE_FIELDS:
        missing = sorted(RESPONSE_FIELDS - set(response))
        additional = sorted(set(response) - RESPONSE_FIELDS)
        if missing:
            errors.append(f"missing fields: {missing}")
        if additional:
            errors.append(f"additional fields: {additional}")

    if "member_code" in response:
        value = response["member_code"]
        if value is not None and (
            not isinstance(value, str) or not value.strip()
        ):
            errors.append("member_code must be a non-empty string or null")

    if "segment" in response and response["segment"] not in ("CASH", "FO", None):
        errors.append("segment must be CASH, FO, or null")

    if "shortfall_amount" in response:
        value = response["shortfall_amount"]
        if value is not None and _decimal(value) is None:
            errors.append("shortfall_amount must be a non-negative decimal string or null")

    if "penalty_slab" in response and response["penalty_slab"] not in ("0.0%", "0.5%", "1.0%", "5.0%", None):
        errors.append("penalty_slab has an invalid value")

    for field in ("explanation", "remediation_action"):
        if field in response and (
            not isinstance(response[field], str) or not response[field].strip()
        ):
            errors.append(f"{field} must be a non-empty string")

    if "severity" in response and response["severity"] not in ("LOW", "MEDIUM", "HIGH", "UNKNOWN"):
        errors.append("severity has an invalid value")

    if "clarification_required" in response and type(
        response["clarification_required"]
    ) is not bool:
        errors.append("clarification_required must be a boolean")

    return {"passed": not errors, "errors": errors}


def layer2_invariants(
    case: dict[str, Any], response: Any
) -> dict[str, Any]:
    """Check calculation invariants and compare all expected fields."""
    expected = case.get("expected_fields", {})
    response = response if isinstance(response, dict) else {}

    amount = _decimal(response.get("shortfall_amount"))
    slab = response.get("penalty_slab")

    if amount is None:
        slab_matches = (
            response.get("shortfall_amount") is None
            and slab is None
        )
    else:
        slab_matches = slab == _slab_for(amount)

    expected_fields_match = all(
        response.get(field) == value
        for field, value in expected.items()
    )

    severity_matches = (
        response.get("severity") == _severity_for(slab)
        if slab in {"0.0%", "0.5%", "1.0%", "5.0%"}
        else response.get("severity") == "UNKNOWN"
    )

    clarification = response.get("clarification_required")
    clarification_consistent = True

    if clarification is True:
        for field in (
            "member_code",
            "segment",
            "shortfall_amount",
            "penalty_slab",
        ):
            if response.get(field) is None:
                continue
            # A clarification response may retain known facts, but must not
            # contradict the expected values for those facts.
            if field in expected and response.get(field) != expected[field]:
                clarification_consistent = False

    elif clarification is False:
        clarification_consistent = all(
            response.get(field) is not None
            for field in (
                "member_code",
                "segment",
                "shortfall_amount",
                "penalty_slab",
            )
        )
    else:
        clarification_consistent = False

    checks = {
        "slab_matches_shortfall": slab_matches,
        "severity_matches_slab": severity_matches,
        "expected_fields_match": expected_fields_match,
        "clarification_consistent": clarification_consistent,
    }

    invariant_checks = (
        slab_matches,
        severity_matches,
        clarification_consistent,
    )
    return {
        "passed": all(invariant_checks),
        "checks": checks,
    }


def _semantic_judge(client: Any) -> Callable:
    """Create a local-model semantic judge with strict JSON-key validation."""

    def judge(
        case: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        assertions = case.get("text_assertions", {})
        keys: list[str] = []

        for field in (
            "explanation_must_cover",
            "explanation_must_not_claim",
            "remediation_must_cover",
        ):
            for index, _ in enumerate(assertions.get(field, []), start=1):
                keys.append(f"{field}_{index}")

        expected_keys = set(keys) | {"understandable", "actionable"}

        prompt = {
            "task": (
                "Evaluate the assistant response against the supplied text "
                "assertions. Do not assume a claim is true merely because "
                "the response states it. Return JSON only."
            ),
            "assertions": assertions,
            "response": response,
            "required_output_keys": sorted(expected_keys),
            "instructions": (
                "Each assertion key must have a boolean value. "
                "For explanation_must_not_claim, true means the response "
                "does not make that prohibited claim. "
                "understandable and actionable must also be booleans. "
                "Do not add any other keys."
            ),
        }

        system_prompt = (
            "You are a strict evaluation judge. Assess only the supplied "
            "response and assertions. Return one JSON object with exactly "
            "the requested keys and boolean values."
        )

        for _ in range(2):
            raw = client.complete(
                system_prompt,
                json.dumps(prompt, ensure_ascii=False),
                json_mode=True,
            )
            try:
                result = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            if (
                isinstance(result, dict)
                and set(result) == expected_keys
                and all(type(value) is bool for value in result.values())
            ):
                return {
                    field: [
                        result[f"{field}_{index}"]
                        for index, _ in enumerate(assertions.get(field, []), start=1)
                    ]
                    for field in (
                        "explanation_must_cover",
                        "explanation_must_not_claim",
                        "remediation_must_cover",
                    )
                } | {
                    "understandable": result["understandable"],
                    "actionable": result["actionable"],
                }

        raise ValueError(
            f"Semantic judge returned invalid JSON or keys for case {case.get('id')}"
        )

    return judge


def _semantic_pass(result: dict[str, Any]) -> bool:
    lists = (
        result.get("explanation_must_cover", []),
        result.get("explanation_must_not_claim", []),
        result.get("remediation_must_cover", []),
    )
    return (
        all(all(items) for items in lists)
        and result.get("understandable") is True
        and result.get("actionable") is True
    )


def evaluate_dataset(
    dataset: dict[str, Any],
    predictions: dict[str, Any],
    semantic_judge: Callable | None = None,
) -> dict[str, Any]:
    """Evaluate predictions and return a detailed report."""
    cases = dataset.get("cases", [])
    evaluation = dataset.get("evaluation", {})
    weights = evaluation.get("case_score_weights", {})

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("Evaluation case weights must have a positive total")

    aggregate_scores: list[float] = []
    case_reports: list[dict[str, Any]] = []
    reviewer_ratings: list[bool] = []

    all_valid_schema = True
    all_calculations_correct = True
    all_clarifications_correct = True
    all_semantics_grounded = True
    pending_count = 0

    for case in cases:
        case_id = case.get("id")
        prediction = predictions.get(case_id, {})
        response = prediction.get("response", {})

        structural = layer1_structural(response)
        invariants = layer2_invariants(case, response)

        expected = case.get("expected_fields", {})

        # Identity and segment extraction are assessed separately from
        # deterministic financial calculation correctness.
        fact_fields = ("member_code", "segment")
        fact_score = (
            sum(response.get(field) == expected.get(field) for field in fact_fields)
            / len(fact_fields)
            if all(field in expected for field in fact_fields)
            else 1.0
        )

        amount_expected = expected.get("shortfall_amount")
        slab_expected = expected.get("penalty_slab")
        amount_actual = response.get("shortfall_amount")
        slab_actual = response.get("penalty_slab")

        if amount_expected is None and slab_expected is None:
            calculation_correct = (
                amount_actual is None and slab_actual is None
            )
        else:
            expected_decimal = _decimal(amount_expected)
            actual_decimal = _decimal(amount_actual)
            calculation_correct = (
                expected_decimal is not None
                and actual_decimal == expected_decimal
                and slab_actual == slab_expected
                and actual_decimal is not None
                and slab_actual == _slab_for(actual_decimal)
            )

        clarification_correct = (
            response.get("clarification_required")
            == expected.get("clarification_required")
        )

        semantic_result: dict[str, Any] = {
            "explanation_must_cover": [],
            "explanation_must_not_claim": [],
            "remediation_must_cover": [],
            "understandable": False,
            "actionable": False,
        }
        if semantic_judge is not None and structural["passed"]:
            semantic_result = semantic_judge(case, response)

        semantic_correct = _semantic_pass(semantic_result)

        schema_score = (
            1.0
            if structural["passed"] and invariants["passed"]
            else 0.0
        )
        calculation_score = 1.0 if calculation_correct else 0.0
        semantic_score = 1.0 if semantic_correct else 0.0
        clarification_score = 1.0 if clarification_correct else 0.0

        case_score = (
            schema_score * weights.get("schema_and_invariants", 0)
            + fact_score * weights.get("fact_extraction", 0)
            + calculation_score * weights.get("shortfall_and_slab", 0)
            + semantic_score
            * weights.get("grounded_explanation_and_remediation", 0)
            + clarification_score
            * weights.get("clarification_behavior", 0)
        ) / total_weight * 100

        aggregate_scores.append(case_score)

        all_valid_schema &= structural["passed"]
        all_calculations_correct &= calculation_correct
        all_clarifications_correct &= clarification_correct
        all_semantics_grounded &= semantic_correct

        rating = prediction.get("reviewer_rating")
        if (
            not isinstance(rating, dict)
            or rating.get("understandable") is None
            or rating.get("actionable") is None
        ):
            pending_count += 1
        else:
            rating_passed = (
                rating.get("understandable") is True
                and rating.get("actionable") is True
            )
            reviewer_ratings.append(rating_passed)

        case_reports.append(
            {
                "id": case_id,
                "score": round(case_score, 2),
                "layers": {
                    "layer1_structural": structural,
                    "layer2_invariants": invariants,
                    "layer3_semantic": {
                        "passed": semantic_correct,
                        "results": semantic_result,
                    },
                },
                "calculation_correct": calculation_correct,
                "fact_extraction_score": round(fact_score * 100, 2),
                "clarification_correct": clarification_correct,
            }
        )

    case_count = len(cases)
    aggregate_score = (
        round(sum(aggregate_scores) / case_count, 2)
        if case_count
        else 0
    )

    reviewer_complete = pending_count == 0 and case_count > 0
    reviewer_rate = (
        round(sum(reviewer_ratings) / len(reviewer_ratings) * 100, 2)
        if reviewer_complete and reviewer_ratings
        else None
    )

    aggregate_minimum = evaluation.get("aggregate_score_minimum", 85)
    reviewer_minimum = evaluation.get(
        "understandable_actionable_rate_minimum", 85
    )

    hard_guards = {
        "valid_schema": bool(all_valid_schema),
        "calculation_correctness": bool(all_calculations_correct),
        "clarification_behavior": bool(all_clarifications_correct),
        "grounded_explanations": bool(all_semantics_grounded),
    }

    passed = (
        aggregate_score >= aggregate_minimum
        and reviewer_rate is not None
        and reviewer_rate >= reviewer_minimum
        and all(hard_guards.values())
    )

    return {
        "case_count": case_count,
        "aggregate_score": aggregate_score,
        "aggregate_score_minimum": aggregate_minimum,
        "understandable_actionable_rate": reviewer_rate,
        "understandable_actionable_rate_minimum": reviewer_minimum,
        "reviewer_ratings_pending_count": pending_count,
        "reviewer_ratings_complete": reviewer_complete,
        "hard_guards": hard_guards,
        "passed": passed,
        "cases": case_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate AI Query Assistant predictions."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evals" / "dataset.json",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=PROJECT_ROOT / "evals" / "predictions.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evals" / "evaluation_report.json",
    )
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))

    report = evaluate_dataset(
        dataset,
        predictions,
        semantic_judge=_semantic_judge(OllamaClient()),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
