"""Command-line entry point for the local shortfall assistant."""

from __future__ import annotations

import argparse
import json
import sys

from assistant import AssistantError, OllamaClient
from prediction_generator import build_response


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explain a clearing-member margin shortfall using local Ollama."
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Natural-language inquiry to process locally.",
    )
    arguments = parser.parse_args(argv)

    try:
        candidate = OllamaClient().extract_facts(arguments.query)
        response = build_response(candidate)
    except (AssistantError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
