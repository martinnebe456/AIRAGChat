from __future__ import annotations

from typing import Any


def build_citations_from_retrieval(retrieved_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for item in retrieved_chunks:
        citations.append(
            {
                "document_id": item.get("document_id"),
                "filename": item.get("filename"),
                "chunk_id": item.get("chunk_id"),
                "snippet": str(item.get("text", ""))[:280],
                "score": item.get("score"),
                "page": item.get("page"),
            }
        )
    return citations


def infer_answer_mode(*, has_context: bool, strict_mode: bool) -> str:
    if not has_context:
        return "no_context_refusal" if strict_mode else "hybrid_general"
    return "rag_grounded"

