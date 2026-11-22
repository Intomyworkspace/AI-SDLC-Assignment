import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from prediction_generator import answer_query, build_response, generate_predictions


def _candidate(**updates: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "member_code": "CM-2001",
        "segment": "CASH",
        "peak_margin_required": "100000",
        "allocated_collateral": "80000",
        "grace_limit_pct": "10",
        "direct_shortfall_amount": None,
        "direct_shortfall_kind": None,
        "evidence": {},
        "explanation_draft": "Candidate facts extracted from the query.",
    }
    candidate.update(updates)
    return candidate


class PredictionGeneratorTests(unittest.TestCase):
    def test_answers_multiple_rule_topics_without_a_client_calculation(self) -> None:
        response = answer_query(
            "How does grace affect short allocation, and what penalty slabs apply?",
            _candidate(
                member_code=None,
                segment=None,
                peak_margin_required=None,
                allocated_collateral=None,
                grace_limit_pct=None,
            ),
        )

        self.assertIn("Raw shortfall = max(0,", response["answer"])
        self.assertIn("Grace reduces the raw shortfall", response["answer"])
        self.assertIn("0.5%", response["answer"])
        self.assertIsNone(response["calculation"])

    def test_answers_varied_wording_with_a_deterministic_client_calculation(self) -> None:
        response = answer_query(
            "CM-2001, CASH. Required margin: INR 100000; allocated collateral: "
            "INR 80000; grace limit 10 percent. What is the short allocation "
            "and applicable rate?",
            _candidate(),
        )

        self.assertIn("For the supplied client details", response["answer"])
        self.assertEqual(response["calculation"]["shortfall_amount"], "10000")
        self.assertEqual(response["calculation"]["penalty_slab"], "0.5%")

    def test_builds_exact_decimal_calculation_and_contract(self) -> None:
        response = build_response(_candidate())

        self.assertEqual(response["shortfall_amount"], "10000")
        self.assertEqual(response["penalty_slab"], "0.5%")
        self.assertEqual(response["severity"], "LOW")
        self.assertFalse(response["clarification_required"])
        self.assertEqual(
            set(response),
            {
                "member_code",
                "segment",
                "shortfall_amount",
                "penalty_slab",
                "explanation",
                "remediation_action",
                "severity",
                "clarification_required",
            },
        )

    def test_preserves_known_calculation_while_clarifying_identity(self) -> None:
        response = build_response(
            _candidate(
                member_code=None,
                peak_margin_required=None,
                allocated_collateral=None,
                grace_limit_pct=None,
                direct_shortfall_amount="50000",
                direct_shortfall_kind="net",
            )
        )

        self.assertTrue(response["clarification_required"])
        self.assertIsNone(response["member_code"])
        self.assertEqual(response["segment"], "CASH")
        self.assertEqual(response["shortfall_amount"], "50000")
        self.assertIn("member code", response["explanation"])

    def test_missing_financial_facts_produce_null_calculation_and_request(self) -> None:
        response = build_response(
            _candidate(
                peak_margin_required=None,
                allocated_collateral="5000",
                grace_limit_pct=None,
            )
        )

        self.assertTrue(response["clarification_required"])
        self.assertIsNone(response["shortfall_amount"])
        self.assertIsNone(response["penalty_slab"])
        self.assertEqual(response["severity"], "UNKNOWN")
        self.assertIn("peak margin", response["remediation_action"])

    def test_generation_uses_queries_not_expected_labels(self) -> None:
        client = Mock()
        client.extract_facts.return_value = _candidate()
        dataset = {
            "cases": [
                {
                    "id": "sample",
                    "query": "Member CM-2001 in CASH has margin and collateral details.",
                    "expected_fields": {"shortfall_amount": "999999"},
                }
            ]
        }

        predictions = generate_predictions(dataset, client)

        self.assertEqual(predictions["sample"]["response"]["shortfall_amount"], "10000")
        self.assertIsNone(
            predictions["sample"]["reviewer_rating"]["understandable"]
        )
        client.extract_facts.assert_called_once_with(dataset["cases"][0]["query"])


if __name__ == "__main__":
    unittest.main()
