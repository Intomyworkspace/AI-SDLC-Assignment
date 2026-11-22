# Quickstart: AI Query & Shortfall Explanation Assistant

## Prerequisites

- Python 3.10 or later.
- Ollama installed and running locally.
- Model `qwen2.5:3b` available locally.
- Development tools `ruff` and `bandit`.

## Prepare the local model

```sh
ollama pull qwen2.5:3b
ollama serve
```

Keep the Ollama service on the local machine. The assistant must not send member inquiry text to an external model or service.

## Run one inquiry

From `part1b`:

```sh
python src/cli.py --query "Member CM-1001 in CASH has peak margin required INR 100000 and allocated collateral INR 80000. Explain the shortfall."
```

The CLI prints one JSON response. If Ollama is unavailable or extraction cannot be validated, it prints an error to stderr and exits nonzero without returning a success-shaped response. When Ollama returns an HTTP error, the message includes its bounded server-provided reason when available.

To limit inference memory use, each Ollama request uses a 2048-token context,
128-token batch, and at most 512 generated tokens. If Ollama still reports an
HTTP 500 for insufficient memory, unload other local models and free system
memory before retrying; the configured model itself needs additional memory
beyond its on-disk size.

## Use the web application

From `part1b`, start the local web server:

```sh
python src/web.py
```

Open `http://127.0.0.1:8000` in a browser and ask one or more related questions
about shortfall, grace, or penalty slabs. You can use prose, bullets, or
key-value details rather than a fixed sentence template. General rule answers
do not require client data; when client facts are supplied, the page also
provides the structured eight-field calculation result. The server binds only
to loopback, and inquiries are sent only to the local Ollama instance. Use
`--port` to select another local port.

## Run checks

```sh
python -m unittest discover -s tests
ruff check src tests .harness
bandit -r src .harness
```

From `part1b`, run the evaluator:

```sh
python .harness/eval_runner.py
```

If `evals/predictions.json` does not exist, the evaluator generates it from the 15 dataset queries using local Ollama extraction and deterministic calculation. To generate only, run `python .harness/generate_predictions.py`. Generated responses do not read `expected_fields`; reviewer ratings are left pending. Review each response and set both `reviewer_rating` values (`understandable` and `actionable`) to `true` or `false`, then rerun the evaluator. It reports the weighted aggregate score and hard guardrails; the overall target remains 85% aggregate and at least 85% reviewer ratings. The boundary cases include net shortfalls of 0, 100000, 100000.01, 1000000, and 1000000.01 INR.
