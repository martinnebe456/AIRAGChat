from __future__ import annotations

from typing import Any


def build_rag_system_prompt(answer_behavior_mode: str) -> str:
    if answer_behavior_mode == "strict_rag_only":
        return (
            "You are a RAG assistant. Answer only from the provided context. "
            "If the context is insufficient, say so clearly. Cite sources as [S1], [S2], ..."
        )
    return (
        "You are a RAG assistant. Prefer the provided context and cite sources as [S1], [S2], ... "
        "If you rely on general knowledge, state that explicitly."
    )


def build_context_prompt(question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    context_lines: list[str] = []
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        snippet = str(chunk.get("text", "")).strip()
        source = chunk.get("filename", "document")
        context_lines.append(f"[S{idx}] {source} | chunk={chunk.get('chunk_id')}\n{snippet}")
    context_blob = "\n\n".join(context_lines)
    return (
        "Question:\n"
        f"{question}\n\n"
        "Retrieved Context:\n"
        f"{context_blob}\n\n"
        "Answer with citations in brackets, for example [S1]."
    )

