from app.rag.chunking.recursive_chunker import chunk_text
from app.rag.citations.citation_utils import build_citations_from_retrieval, infer_answer_mode
from app.rag.prompts.prompt_builder import build_context_prompt


def test_chunk_text_produces_deterministic_ids():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunk_text("doc-1", text, chunk_size=20, chunk_overlap=5)
    assert len(chunks) >= 2
    chunks_again = chunk_text("doc-1", text, chunk_size=20, chunk_overlap=5)
    assert [c.chunk_id for c in chunks] == [c.chunk_id for c in chunks_again]


def test_citation_build_and_answer_mode():
    retrieved = [
        {"document_id": "d1", "filename": "a.txt", "chunk_id": "c1", "text": "alpha beta gamma", "score": 0.9}
    ]
    citations = build_citations_from_retrieval(retrieved)
    assert citations[0]["filename"] == "a.txt"
    assert infer_answer_mode(has_context=True, strict_mode=True) == "rag_grounded"
    assert infer_answer_mode(has_context=False, strict_mode=True) == "no_context_refusal"


def test_prompt_builder_includes_sources():
    prompt = build_context_prompt("What is alpha?", [{"filename": "a.txt", "chunk_id": "c1", "text": "alpha"}])
    assert "[S1]" in prompt
    assert "What is alpha?" in prompt

