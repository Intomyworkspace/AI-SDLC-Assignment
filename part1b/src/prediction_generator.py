"""Generate evaluation responses from local model extraction and fixed rules."""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from assistant import AssistantError, OllamaClient


def _decimal(value: str) -> Decimal:
    return Decimal(value)


def _format_amount(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def _slab_for(amount: Decimal) -> tuple[str, str]:
    if amount == 0:
        return "0.0%", "LOW"
    if amount <= Decimal(100000):
        return "0.5%", "LOW"
    if amount <= Decimal(1000000):
        return "1.0%", "MEDIUM"
    return "5.0%", "HIGH"


def build_response(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Build the public response using extracted facts and deterministic math."""
    member_code = candidate["member_code"]
    segment = candidate["segment"]
    peak_text = candidate["peak_margin_required"]
    collateral_text = candidate["allocated_collateral"]
    grace_text = candidate["grace_limit_pct"]
    direct_text = candidate["direct_shortfall_amount"]
    direct_kind = candidate["direct_shortfall_kind"]

    peak = _decimal(peak_text) if peak_text is not None else None
    collateral = _decimal(collateral_text) if collateral_text is not None else None
    grace_pct = _decimal(grace_text) if grace_text is not None else None
    direct = _decimal(direct_text) if direct_text is not None else None
    missing: list[str] = []
    raw_shortfall: Decimal | None = None
    grace_amount: Decimal | None = None
    shortfall: Decimal | None = None

    if direct is not None and direct_kind == "net":
        shortfall = direct
    elif direct is not None and direct_kind == "raw":
        if peak is None:
            missing.append("the required peak margin")
        if grace_pct is None:
            missing.append("the grace limit percentage")
        if peak is not None and grace_pct is not None:
            grace_amount = peak * grace_pct / Decimal(100)
            raw_shortfall = direct
            shortfall = max(Decimal(0), direct - grace_amount)
    elif peak is not None and collateral is not None:
        raw_shortfall = max(Decimal(0), peak - collateral)
        applied_grace_pct = grace_pct or Decimal(0)
        grace_amount = peak * applied_grace_pct / Decimal(100)
        shortfall = max(Decimal(0), raw_shortfall - grace_amount)
    else:
        if peak is None:
            missing.append("the required peak margin")
        if collateral is None:
            missing.append("the allocated collateral")
        if direct is None and not missing:
            missing.append("the net chargeable shortfall")

    if member_code is None:
        missing.insert(0, "the member code")
    if segment is None:
        missing.insert(1 if member_code is None else 0, "the segment (CASH or FO)")

    clarification = bool(missing)
    if shortfall is None:
        slab = None
        severity = "UNKNOWN"
    else:
        slab, severity = _slab_for(shortfall)

    explanation_parts: list[str] = []
    if member_code is None:
        explanation_parts.append("Please provide the member code.")
    if segment is None:
        explanation_parts.append("Please confirm whether the segment is CASH or FO.")
    if shortfall is None:
        if peak is None and collateral is None and direct is None:
            explanation_parts.append(
                "Please provide peak margin and allocated collateral, or confirm the net chargeable shortfall."
            )
        else:
            for item in missing:
                if item == "the member code" or item == "the segment (CASH or FO)":
                    continue
                label = item.removeprefix("the ")
                explanation_parts.append(f"Please provide a valid {label}.")
    elif raw_shortfall is not None and peak is not None and collateral is not None:
        if collateral >= peak:
            explanation_parts.append(
                "Allocated collateral meets or exceeds required peak margin; there is no chargeable shortfall."
            )
        elif shortfall == 0 and grace_amount is not None and grace_amount >= raw_shortfall:
            if grace_amount == raw_shortfall:
                explanation_parts.append(
                    "Grace exactly offsets the raw shortfall; the net shortfall is INR 0."
                )
            else:
                explanation_parts.append(
                    "Grace exceeds the raw shortfall; the net shortfall is clamped to zero."
                )
        else:
            explanation_parts.append(
                f"Raw shortfall is INR {_format_amount(raw_shortfall)}."
            )
            if grace_pct is not None:
                explanation_parts.append(
                    f"Applying grace of {_format_amount(grace_pct)}% gives a net chargeable shortfall of INR {_format_amount(shortfall)}."
                )
            else:
                explanation_parts.append(
                    f"Net chargeable shortfall is INR {_format_amount(shortfall)}."
                )
        explanation_parts.append(f"The applicable penalty slab is {slab}.")
    else:
        explanation_parts.append(
            f"The supplied net chargeable shortfall is INR {_format_amount(shortfall)}; the applicable slab is {slab}."
        )

    if shortfall is None:
        remediation_parts = []
        if member_code is None:
            remediation_parts.append("provide the member code")
        if segment is None:
            remediation_parts.append("confirm whether the segment is CASH or FO")
        if peak is None and direct_kind != "net":
            remediation_parts.append("provide a valid non-negative peak margin amount")
        if collateral is None and direct is None:
            remediation_parts.append(
                "provide a valid non-negative allocated collateral amount"
            )
        if direct_kind == "raw" and grace_pct is None:
            remediation_parts.append("provide the grace limit percentage")
        if not remediation_parts:
            remediation_parts.append("confirm the net chargeable shortfall")
        remediation = "Please " + "; ".join(remediation_parts) + "."
    elif shortfall == 0:
        remediation = "No top-up is indicated by the supplied values."
    else:
        remediation = (
            "Review collateral allocation against the remaining shortfall and arrange any required top-up."
        )

    return {
        "member_code": member_code,
        "segment": segment,
        "shortfall_amount": _format_amount(shortfall) if shortfall is not None else None,
        "penalty_slab": slab,
        "explanation": " ".join(explanation_parts),
        "remediation_action": remediation,
        "severity": severity,
        "clarification_required": clarification,
    }


def answer_query(
    query: str, candidate: Mapping[str, Any]
) -> dict[str, Any]:
    """Answer supported domain topics and attach a calculation when facts exist."""
    normalized_query = query.casefold()
    topics: list[str] = []

    if re.search(
        r"\b(shortfall|short allocation|short|shortage|margin)\b",
        normalized_query,
    ):
        topics.append(
            "Raw shortfall = max(0, required peak margin - allocated collateral). "
            "If a grace limit applies, allowable grace = peak margin * grace "
            "percentage / 100; net chargeable shortfall = max(0, raw shortfall "
            "- allowable grace)."
        )
    if re.search(r"\b(grace|grace limit)\b", normalized_query):
        topics.append(
            "Grace reduces the raw shortfall by peak margin * grace limit / 100. "
            "The net shortfall cannot be less than zero."
        )
    if re.search(r"\b(penalty|slab|rate|charge|fine)\b", normalized_query):
        topics.append(
            "The applicable slab is 0.0% for a zero net shortfall, 0.5% for "
            "a positive shortfall up to and including INR 100,000, 1.0% for "
            "more than INR 100,000 up to and including INR 1,000,000, and "
            "5.0% for more than INR 1,000,000. These are slab rates, not a "
            "calculation of the total penalty amount."
        )
    if re.search(
        r"\b(what (?:details|information|inputs)|what do i need)\b",
        normalized_query,
    ):
        topics.append(
            "To check a specific client, provide the member code and CASH or FO "
            "segment, plus required peak margin and allocated collateral. "
            "Include the grace limit percentage when it applies."
        )

    calculation_fields = (
        "peak_margin_required",
        "allocated_collateral",
        "grace_limit_pct",
        "direct_shortfall_amount",
    )
    has_client_facts = (
        any(candidate.get(field) is not None for field in calculation_fields)
        or candidate.get("member_code") is not None
        or candidate.get("segment") is not None
    )
    calculation = build_response(candidate) if has_client_facts else None

    if calculation is not None:
        topics.append(
            "For the supplied client details: "
            f"{calculation['explanation']} "
            f"{calculation['remediation_action']}"
        )
    elif not topics:
        topics.append(
            "I can help with shortfall calculations, grace treatment, and penalty "
            "slab questions. For a specific client calculation, provide the "
            "member code, CASH or FO segment, required peak margin, allocated "
            "collateral, and any applicable grace limit."
        )

    return {
        "answer": " ".join(topics),
        "calculation": calculation,
    }


def generate_predictions(
    dataset: Mapping[str, Any],
    client: OllamaClient,
) -> dict[str, Any]:
    """Extract each query locally and generate responses without reading labels."""
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("dataset cases must be a non-empty list")
    predictions: dict[str, Any] = {}
    for case in cases:
        if not isinstance(case, Mapping):
            raise TypeError("every dataset case must be an object")
        case_id = case.get("id")
        query = case.get("query")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("every dataset case must have a non-empty id")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"{case_id}: query must be a non-empty string")
        try:
            facts = client.extract_facts(query)
        except AssistantError as error:
            raise AssistantError(f"{case_id}: {error}") from error
        response = build_response(facts)
        predictions[case_id] = {
            "response": response,
            "reviewer_rating": {
                "understandable": None,
                "actionable": None,
            },
        }
    return predictions
