import json
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from assistant import (
    MODEL_NAME,
    OLLAMA_BATCH_TOKENS,
    OLLAMA_CONTEXT_TOKENS,
    OLLAMA_MAX_OUTPUT_TOKENS,
    AssistantError,
    OllamaClient,
)


class _FakeResponse:
    def __init__(self, value: dict[str, object]) -> None:
        self._body = json.dumps(value).encode("utf-8")

    def __enter__(self) -> object:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class OllamaClientTests(unittest.TestCase):
    def _candidate(self) -> dict[str, object]:
        return {
            "member_code": "CM-2001",
            "segment": "CASH",
            "peak_margin_required": "100000",
            "allocated_collateral": "80000",
            "grace_limit_pct": "10",
            "direct_shortfall_amount": None,
            "direct_shortfall_kind": None,
            "evidence": {
                "member_code": "CM-2001",
                "segment": "CASH",
                "peak_margin_required": "100000",
                "allocated_collateral": "80000",
                "grace_limit_pct": "10 percent",
            },
            "explanation_draft": "The inquiry includes margin, collateral, and grace values.",
        }

    def test_extracts_candidate_facts_from_local_qwen_response(self) -> None:
        content = json.dumps(self._candidate())
        response = _FakeResponse(
            {
                "model": MODEL_NAME,
                "message": {"content": content},
            }
        )
        client = OllamaClient()

        with patch("assistant.urlopen", return_value=response) as urlopen:
            facts = client.extract_facts(
                "Member CM-2001 in CASH has margin 100000, collateral 80000, grace 10 percent."
            )

        self.assertEqual(facts["member_code"], "CM-2001")
        self.assertEqual(facts["peak_margin_required"], "100000")
        self.assertNotIn("shortfall_amount", facts)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], MODEL_NAME)
        self.assertEqual(payload["options"]["num_ctx"], OLLAMA_CONTEXT_TOKENS)
        self.assertEqual(payload["options"]["num_batch"], OLLAMA_BATCH_TOKENS)
        self.assertEqual(
            payload["options"]["num_predict"], OLLAMA_MAX_OUTPUT_TOKENS
        )

    def test_rejects_non_loopback_ollama_host(self) -> None:
        with patch("assistant.urlopen") as urlopen, self.assertRaises(
            AssistantError
        ):
            OllamaClient(base_url="https://example.com")
        urlopen.assert_not_called()

    def test_timeout_must_be_positive_and_bounded(self) -> None:
        with self.assertRaises(TypeError):
            OllamaClient(timeout=True)
        with self.assertRaises(ValueError):
            OllamaClient(timeout=301)

    def test_reports_local_ollama_unavailability_without_fallback(self) -> None:
        with patch(
            "assistant.urlopen", side_effect=URLError("offline")
        ) as urlopen, self.assertRaisesRegex(
            AssistantError, "could not reach local Ollama"
        ):
            OllamaClient().complete("system", "query")

        urlopen.assert_called_once()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")

    def test_includes_ollama_http_error_detail(self) -> None:
        error = HTTPError(
            "http://127.0.0.1:11434/api/chat",
            500,
            "Internal Server Error",
            hdrs=None,
            fp=BytesIO(
                b'{"error":"model requires more memory than is available"}'
            ),
        )

        with patch("assistant.urlopen", side_effect=error), self.assertRaisesRegex(
            AssistantError,
            "local Ollama returned HTTP 500: model requires more memory",
        ):
            OllamaClient().complete("system", "query")

    def test_rejects_malformed_model_candidate_json(self) -> None:
        response = _FakeResponse(
            {"model": MODEL_NAME, "message": {"content": "not JSON"}}
        )
        with patch("assistant.urlopen", return_value=response), self.assertRaisesRegex(
            AssistantError, "not valid candidate JSON"
        ):
            OllamaClient().extract_facts("Explain the shortfall.")

    def test_rejects_unexpected_model_response(self) -> None:
        client = OllamaClient()
        response = _FakeResponse(
            {
                "model": "another-model",
                "message": {"content": "{}"},
            }
        )
        with patch("assistant.urlopen", return_value=response), self.assertRaisesRegex(
            AssistantError, "unexpected model"
        ):
            client.complete("system", "user")

    def test_discards_candidate_facts_without_query_evidence(self) -> None:
        candidate = self._candidate()
        candidate["evidence"] = {
            "member_code": "CM-2001",
            "segment": "CASH",
            "peak_margin_required": "100000",
            "allocated_collateral": "80000",
            "grace_limit_pct": "10 percent",
        }
        response = _FakeResponse(
            {
                "model": MODEL_NAME,
                "message": {"content": json.dumps(candidate)},
            }
        )
        with patch("assistant.urlopen", return_value=response):
            facts = OllamaClient().extract_facts(
                "Member CM-2001 in CASH has margin 100000 and collateral 80000."
            )

        self.assertIsNone(facts["grace_limit_pct"])
        self.assertNotIn("grace_limit_pct", facts["evidence"])

    def test_recovers_exact_numeric_quote_when_model_paraphrases_context(self) -> None:
        candidate = self._candidate()
        evidence = candidate["evidence"]
        assert isinstance(evidence, dict)
        evidence["peak_margin_required"] = "required margin 100000"

        validated = OllamaClient._validate_candidate(
            candidate,
            "Member CM-2001 in CASH has peak margin required is INR 100000, "
            "allocated collateral 80000, grace limit 10 percent.",
        )

        self.assertEqual(
            validated["evidence"]["peak_margin_required"],
            "100000",
        )

    def test_accepts_allocation_label_and_rejects_ambiguous_segment(self) -> None:
        candidate = self._candidate()
        evidence = candidate["evidence"]
        assert isinstance(evidence, dict)
        evidence["allocated_collateral"] = "allocation INR 80000"

        validated = OllamaClient._validate_candidate(
            candidate,
            "Member CM-2001: CASH, peak margin 100000; allocation INR 80000.",
        )

        self.assertEqual(validated["allocated_collateral"], "80000")
        self.assertEqual(validated["segment"], "CASH")

        ambiguous = self._candidate()
        evidence = ambiguous["evidence"]
        assert isinstance(evidence, dict)
        evidence["segment"] = "CASH"
        validated = OllamaClient._validate_candidate(
            ambiguous,
            "What details do I need, CASH or FO?",
        )

        self.assertIsNone(validated["segment"])

    def test_invalid_monetary_candidate_becomes_unknown(self) -> None:
        candidate = self._candidate()
        candidate["peak_margin_required"] = "-1000"
        evidence = candidate["evidence"]
        assert isinstance(evidence, dict)
        evidence["peak_margin_required"] = "peak margin -1000"

        validated = OllamaClient._validate_candidate(
            candidate,
            "Member CM-2001 in CASH has peak margin -1000 and collateral 80000.",
        )

        self.assertIsNone(validated["peak_margin_required"])


if __name__ == "__main__":
    unittest.main()
