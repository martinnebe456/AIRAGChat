from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    chunk_id: str
    index: int
    text: str
    source_page: int | None = None


def _split_text(text: str, max_chars: int) -> list[str]:
    separators = ["\n\n", "\n", ". ", " "]
    segments = [text]
    for sep in separators:
        next_segments: list[str] = []
        for seg in segments:
            if len(seg) <= max_chars:
                next_segments.append(seg)
                continue
            parts = seg.split(sep)
            if len(parts) == 1:
                next_segments.append(seg)
                continue
            current = ""
            for part in parts:
                candidate = (current + (sep if current else "") + part).strip()
                if len(candidate) <= max_chars:
                    current = candidate
                else:
                    if current:
                        next_segments.append(current)
                    current = part.strip()
            if current:
                next_segments.append(current)
        segments = next_segments
    final: list[str] = []
    for seg in segments:
        if len(seg) <= max_chars:
            final.append(seg)
            continue
        for i in range(0, len(seg), max_chars):
            final.append(seg[i : i + max_chars])
    return [s.strip() for s in final if s.strip()]


def chunk_text(
    document_id: str,
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    *,
    start_index: int = 0,
    source_page: int | None = None,
) -> list[TextChunk]:
    base_segments = _split_text(text, chunk_size)
    chunks: list[TextChunk] = []
    for idx, seg in enumerate(base_segments):
        logical_idx = start_index + idx
        if chunk_overlap and idx > 0:
            prefix = base_segments[idx - 1][-chunk_overlap:]
            seg = f"{prefix}\n{seg}"
        chunk_id = hashlib.sha1(f"{document_id}:{logical_idx}:{seg}".encode("utf-8")).hexdigest()[:20]
        chunks.append(TextChunk(chunk_id=chunk_id, index=logical_idx, text=seg, source_page=source_page))
    return chunks
