"""Evidence-based retrieval metrics; human quality labels remain separate."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check full gold evidence in a single retrieved chunk, including alternatives."""
    gold = [{"source_id": question["gold_source_id"], "page": question["gold_page"],
             "evidence_quote": question["evidence_quote"]}]
    gold.extend(question.get("alternative_gold", []))
    evaluated = []
    for rank, hit in enumerate(hits, start=1):
        match = next((item for item in gold
                      if hit["document_id"] == item["source_id"]
                      and hit["page"] == item["page"]
                      and _fold(item["evidence_quote"]) in _fold(hit["text"])), None)
        evaluated.append({"rank": rank, **hit, "evidence_hit": match is not None,
                          "matched_gold": match})
    return {
        "id": question["id"],
        "split": question["split"],
        "type": question.get("type"),
        "question": question["question"],
        "expected_answer": question["expected_answer"],
        "filter": question.get("filter"),
        "gold": gold,
        "hits": evaluated,
        "hit_at_1": bool(evaluated and evaluated[0]["evidence_hit"]),
        "evidence_hit_at_3": any(hit["evidence_hit"] for hit in evaluated[:3]),
        "manual_grounding_label": None,
        "manual_grounding_reason": None,
    }


def _fold(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Return numerator and denominator for each strategy/split without pooling."""
    result: dict[str, dict[str, Any]] = {}
    for trace in traces:
        key = f"{trace['strategy']}:{trace['split']}"
        counts = result.setdefault(key, {"strategy": trace["strategy"],
                                         "split": trace["split"], "questions": 0,
                                         "hit_at_1": 0, "evidence_hit_at_3": 0})
        counts["questions"] += 1
        counts["hit_at_1"] += int(trace["hit_at_1"])
        counts["evidence_hit_at_3"] += int(trace["evidence_hit_at_3"])
    return result
