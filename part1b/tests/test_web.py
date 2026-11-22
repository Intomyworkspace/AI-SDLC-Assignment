import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import web


class WebApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), web.RequestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def _post(self, value: object) -> tuple[int, dict[str, object]]:
        request = Request(
            f"{self.base_url}/api/query",
            data=json.dumps(value).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            body = json.loads(error.read())
            error.close()
            return error.code, body

    def test_serves_browser_form(self) -> None:
        with urlopen(self.base_url) as response:
            page = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn('id="query"', page)
        self.assertIn('"/api/query"', page)

    def test_returns_conversational_answer_and_structured_calculation(self) -> None:
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
        with patch.object(web, "OllamaClient") as client_class:
            client_class.return_value.extract_facts.return_value = facts

            status, response = self._post(
                {
                    "query": "CM-2001 in CASH has margin 100000 and collateral "
                    "80000. How much short and what penalty slab?"
                }
            )

        self.assertEqual(status, 200)
        self.assertEqual(set(response), {"answer", "calculation"})
        self.assertIn("For the supplied client details", response["answer"])
        self.assertEqual(response["calculation"]["shortfall_amount"], "20000")
        self.assertEqual(response["calculation"]["penalty_slab"], "0.5%")
        self.assertFalse(response["calculation"]["clarification_required"])
        client_class.return_value.extract_facts.assert_called_once_with(
            "CM-2001 in CASH has margin 100000 and collateral "
            "80000. How much short and what penalty slab?"
        )

    def test_answers_general_rule_question_without_fabricating_calculation(self) -> None:
        facts = {
            "member_code": None,
            "segment": None,
            "peak_margin_required": None,
            "allocated_collateral": None,
            "grace_limit_pct": None,
            "direct_shortfall_amount": None,
            "direct_shortfall_kind": None,
            "evidence": {},
            "explanation_draft": "No client calculation was requested.",
        }
        with patch.object(web, "OllamaClient") as client_class:
            client_class.return_value.extract_facts.return_value = facts

            status, response = self._post(
                {"query": "How does grace affect shortfall and penalty slabs?"}
            )

        self.assertEqual(status, 200)
        self.assertIn("Grace reduces the raw shortfall", response["answer"])
        self.assertIn("0.5%", response["answer"])
        self.assertIsNone(response["calculation"])

    def test_rejects_empty_inquiry_without_calling_model(self) -> None:
        with patch.object(web, "OllamaClient") as client_class:
            status, response = self._post({"query": "  "})

        self.assertEqual(status, 400)
        self.assertIn("non-empty", response["error"])
        client_class.assert_not_called()

    def test_returns_local_ollama_failure_as_an_explicit_api_error(self) -> None:
        message = "local Ollama returned HTTP 500: model requires more memory"
        with patch.object(web, "OllamaClient") as client_class:
            client_class.return_value.extract_facts.side_effect = web.AssistantError(
                message
            )

            status, response = self._post({"query": "Explain the penalty slab."})

        self.assertEqual(status, 502)
        self.assertEqual(response, {"error": message})


if __name__ == "__main__":
    unittest.main()
