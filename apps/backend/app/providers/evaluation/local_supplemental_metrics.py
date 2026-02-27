from __future__ import annotations

from typing import Any


def compute_supplemental_metrics(
    *,
    expected_sources: list[str] | None,
    retrieved_chunk_ids: list[str],
    answer: str,
    citations_present: bool,
    expects_refusal: bool,
) -> dict[str, Any]:
    expected_set = set(expected_sources or [])
    retrieved_set = set(retrieved_chunk_ids)
    hit = 1.0 if expected_set and expected_set.intersection(retrieved_set) else 0.0
    recall = (len(expected_set.intersection(retrieved_set)) / len(expected_set)) if expected_set else None
    refusal_flag = "insufficient" in answer.lower() or "no relevant context" in answer.lower()
    return {
        "hit_at_k": hit if expected_set else None,
        "recall_at_k": recall,
        "citation_presence": 1.0 if citations_present else 0.0,
        "refusal_correctness": 1.0 if (expects_refusal == refusal_flag) else 0.0,
    }

