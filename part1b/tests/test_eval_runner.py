import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = PROJECT_ROOT / ".harness" / "eval_runner.py"
SPEC = importlib.util.spec_from_file_location("eval_runner", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load evaluation runner from {RUNNER_PATH}")
eval_runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = eval_runner
SPEC.loader.exec_module(eval_runner)


class EvaluationRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = {
            "id": "test-case",
            "expected_fields": {
                "member_code": "CM-3001",
                "segment": "CASH",
                "shortfall_amount": "20000",
                "penalty_slab": "0.5%",
                "severity": "LOW",
                "clarification_required": False,
            },
            "text_assertions": {
                "explanation_must_cover": ["net shortfall is INR 20000"],
                "explanation_must_not_claim": ["an unsupported deadline"],
                "remediation_must_cover": ["review collateral"],
            },
        }
        self.response = {
            "member_code": "CM-3001",
            "segment": "CASH",
            "shortfall_amount": "20000",
            "penalty_slab": "0.5%",
            "explanation": "The net shortfall is INR 20000 at the 0.5% slab.",
            "remediation_action": "Review collateral allocation.",
            "severity": "LOW",
            "clarification_required": False,
        }

    def _semantic_judge(
        self,
        case: dict[str, object],
        response: dict[str, object],
    ) -> dict[str, object]:
        assertions = case["text_assertions"]
        return {
            key: [True] * len(assertions.get(key, []))
            for key in (
                "explanation_must_cover",
                "explanation_must_not_claim",
                "remediation_must_cover",
            )
        } | {"understandable": True, "actionable": True}

    def test_layer_one_rejects_missing_and_additional_fields(self) -> None:
        self.assertTrue(eval_runner.layer1_structural(self.response)["passed"])
        malformed = dict(self.response)
        malformed["extra"] = "not allowed"
        self.assertFalse(eval_runner.layer1_structural(malformed)["passed"])
        malformed = dict(self.response, severity=[])
        self.assertFalse(eval_runner.layer1_structural(malformed)["passed"])

    def test_layer_two_detects_slab_invariant_failure(self) -> None:
        wrong = dict(self.response, penalty_slab="1.0%")
        result = eval_runner.layer2_invariants(self.case, wrong)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["slab_matches_shortfall"])

    def test_evaluates_three_layers_and_reviewer_rate(self) -> None:
        dataset = {
            "case_count": 1,
            "evaluation": {
                "aggregate_score_minimum": 85,
                "understandable_actionable_rate_minimum": 85,
                "case_score_weights": {
                    "schema_and_invariants": 20,
                    "fact_extraction": 25,
                    "shortfall_and_slab": 25,
                    "grounded_explanation_and_remediation": 15,
                    "clarification_behavior": 15,
                },
            },
            "cases": [self.case],
        }
        predictions = {
            "test-case": {
                "response": self.response,
                "reviewer_rating": {
                    "understandable": True,
                    "actionable": True,
                },
            }
        }

        report = eval_runner.evaluate_dataset(
            dataset,
            predictions,
            semantic_judge=self._semantic_judge,
        )

        self.assertEqual(report["case_count"], 1)
        self.assertEqual(report["aggregate_score"], 100)
        self.assertEqual(report["understandable_actionable_rate"], 100)
        self.assertTrue(report["passed"])

    def test_reviewer_rate_below_threshold_fails_evaluation(self) -> None:
        cases = []
        predictions = {}
        for index in range(5):
            case = dict(self.case, id=f"test-case-{index}")
            cases.append(case)
            predictions[case["id"]] = {
                "response": self.response,
                "reviewer_rating": {
                    "understandable": index != 0,
                    "actionable": True,
                },
            }
        dataset = {
            "case_count": len(cases),
            "evaluation": {
                "aggregate_score_minimum": 85,
                "understandable_actionable_rate_minimum": 85,
                "case_score_weights": {
                    "schema_and_invariants": 20,
                    "fact_extraction": 25,
                    "shortfall_and_slab": 25,
                    "grounded_explanation_and_remediation": 15,
                    "clarification_behavior": 15,
                },
            },
            "cases": cases,
        }

        report = eval_runner.evaluate_dataset(
            dataset,
            predictions,
            semantic_judge=self._semantic_judge,
        )

        self.assertEqual(report["understandable_actionable_rate"], 80)
        self.assertFalse(report["passed"])

    def test_pending_reviewer_ratings_are_not_counted_as_rejections(self) -> None:
        dataset = {
            "case_count": 1,
            "evaluation": {
                "aggregate_score_minimum": 85,
                "understandable_actionable_rate_minimum": 85,
                "case_score_weights": {
                    "schema_and_invariants": 20,
                    "fact_extraction": 25,
                    "shortfall_and_slab": 25,
                    "grounded_explanation_and_remediation": 15,
                    "clarification_behavior": 15,
                },
            },
            "cases": [self.case],
        }
        predictions = {
            "test-case": {
                "response": self.response,
                "reviewer_rating": {
                    "understandable": None,
                    "actionable": None,
                },
            }
        }

        report = eval_runner.evaluate_dataset(
            dataset,
            predictions,
            semantic_judge=self._semantic_judge,
        )

        self.assertIsNone(report["understandable_actionable_rate"])
        self.assertEqual(report["reviewer_ratings_pending_count"], 1)
        self.assertFalse(report["reviewer_ratings_complete"])
        self.assertFalse(report["passed"])

    def test_semantic_judge_retries_invalid_key_set(self) -> None:
        valid = {
            "explanation_must_cover_1": True,
            "explanation_must_not_claim_1": True,
            "remediation_must_cover_1": True,
            "understandable": True,
            "actionable": True,
        }
        invalid = dict(valid, extra=True)
        client = Mock()
        client.complete.side_effect = [json.dumps(invalid), json.dumps(valid)]

        result = eval_runner._semantic_judge(client)(self.case, self.response)

        self.assertEqual(
            result,
            self._semantic_judge(self.case, self.response),
        )
        self.assertEqual(client.complete.call_count, 2)

    def test_calculation_guard_is_independent_of_identity_extraction(self) -> None:
        dataset = {
            "case_count": 1,
            "evaluation": {
                "aggregate_score_minimum": 85,
                "understandable_actionable_rate_minimum": 85,
                "case_score_weights": {
                    "schema_and_invariants": 20,
                    "fact_extraction": 25,
                    "shortfall_and_slab": 25,
                    "grounded_explanation_and_remediation": 15,
                    "clarification_behavior": 15,
                },
            },
            "cases": [self.case],
        }
        response = dict(self.response, member_code="CM-WRONG")
        predictions = {
            "test-case": {
                "response": response,
                "reviewer_rating": {
                    "understandable": True,
                    "actionable": True,
                },
            }
        }

        report = eval_runner.evaluate_dataset(
            dataset,
            predictions,
            semantic_judge=self._semantic_judge,
        )

        self.assertTrue(report["hard_guards"]["calculation_correctness"])
        self.assertFalse(
            report["cases"][0]["layers"]["layer2_invariants"]["checks"][
                "expected_fields_match"
            ]
        )

    def test_dataset_file_has_exactly_fifteen_cases(self) -> None:
        dataset = json.loads((PROJECT_ROOT / "evals" / "dataset.json").read_text())
        self.assertEqual(dataset["case_count"], 15)
        self.assertEqual(len(dataset["cases"]), 15)


if __name__ == "__main__":
    unittest.main()
