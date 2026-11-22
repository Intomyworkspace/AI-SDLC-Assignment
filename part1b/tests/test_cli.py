import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import cli
from assistant import AssistantError


class CliTests(unittest.TestCase):
    def test_prints_structured_response_json(self) -> None:
        facts = {
            "member_code": "CM-2001",
            "segment": "CASH",
            "peak_margin_required": "100000",
            "allocated_collateral": "80000",
            "grace_limit_pct": None,
            "direct_shortfall_amount": None,
            "direct_shortfall_kind": None,
            "evidence": {},
            "explanation_draft": "Extracted from the query.",
        }
        client = Mock()
        client.extract_facts.return_value = facts
        output = io.StringIO()
        errors = io.StringIO()

        with (
            patch.object(cli, "OllamaClient", return_value=client),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            result = cli.main(["--query", "Explain the margin shortfall"])

        response = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(response["shortfall_amount"], "20000")
        self.assertEqual(response["penalty_slab"], "0.5%")
        self.assertFalse(response["clarification_required"])
        self.assertEqual(errors.getvalue(), "")

    def test_model_failure_reports_error_without_json_response(self) -> None:
        client = Mock()
        client.extract_facts.side_effect = AssistantError("local model unavailable")
        output = io.StringIO()
        errors = io.StringIO()

        with (
            patch.object(cli, "OllamaClient", return_value=client),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            result = cli.main(["--query", "Explain the margin shortfall"])

        self.assertEqual(result, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("local model unavailable", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
