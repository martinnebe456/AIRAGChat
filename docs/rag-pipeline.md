# RAG Pipeline

## Ingestion Flow

1. Upload file via `/api/v1/documents/upload`
2. Save document metadata in PostgreSQL (`documents`)
3. Store original file on mounted volume (`data/uploads`)
4. Create processing job (`document_processing_jobs`)
5. Queue Celery ingestion task
6. Parse text (`txt`, `md`, `pdf`, `docx`)
7. Normalize text
8. Chunk text (configurable size/overlap)
9. Generate embeddings (CPU-first local embedding provider)
10. Upsert chunk vectors and metadata into Qdrant
11. Mark document status `indexed` or `failed`
12. Expose processing events/logs in UI/API

## Supported File Types (MVP)

- `.txt`
- `.md`
- `.pdf` (text-based extraction)
- `.docx`

OCR for scanned PDFs is out of MVP scope (planned extension).

## Chunking

The current chunker uses separator-aware splitting with overlap:

- paragraph boundaries first
- line boundaries next
- sentence/space fallback
- hard split if needed

Chunk IDs are deterministic per document/chunk content to support reproducible indexing behavior.

## Embeddings

Default embedding model:

- `intfloat/multilingual-e5-small`

The embedding provider is implemented behind an abstraction and uses `query:` / `passage:` prefixes. A deterministic fallback embedding path exists to keep development/test flows operable when model download is unavailable.

## Retrieval

Chat retrieval flow:

1. Embed query
2. Search Qdrant top-k
3. Optional filter by document IDs
4. Threshold check for context sufficiency
5. Build prompt + citations
6. Call active inference provider

## Guardrails

Configurable policy:

- `strict_rag_only`
- `hybrid_with_disclaimer`

When insufficient context is found in strict mode, the backend refuses instead of hallucinating a sourced answer.

