# Architecture

## System Topology

- `frontend` (React SPA) calls `backend` only.
- `backend` exposes REST APIs, enforces auth/RBAC, and persists metadata.
- `worker` (Celery) performs ingestion and evaluation jobs.
- `postgres` stores users, settings, documents metadata, chats, audit logs, evals.
- `qdrant` stores chunk vectors + payload metadata.
- `redis` provides queue broker/result backend.
- observability services (`otel-collector`, `jaeger`, `prometheus`, `grafana`, `loki`) support local tracing/metrics/logs.

## Backend Layering

- `api/routes`: thin controllers + request/response models
- `api/deps`: auth token parsing and RBAC dependencies
- `services`: business logic (auth, users, docs, chat, evals, settings)
- `providers`: inference/embedding/eval abstractions and implementations
- `rag`: parsing, chunking, prompt assembly, citations helpers
- `workers`: Celery task entry points
- `db/models`: SQLAlchemy entities

## Core Runtime Flow (OpenAI-only)

1. Frontend sends chat question to backend.
2. Backend retrieves top-k chunks from Qdrant.
3. Backend builds RAG prompt and citations.
4. Backend resolves the active OpenAI chat model from settings.
5. Backend calls `OpenAIInferenceProvider`.
6. OpenAI returns a response using the selected model.
7. Backend stores chat messages + model usage metadata and returns cited answer.

## Provider Mode

Runtime is OpenAI-only:

- active provider is fixed to `openai_api`
- OpenAI API key stored encrypted in `secrets_store`
- backend-only OpenAI calls

## Data Stores

### PostgreSQL

Stores:

- users, refresh tokens
- documents, processing jobs/events
- chat sessions/messages
- system/provider settings
- secrets metadata
- audit logs
- evaluation datasets/runs/results
- model usage logs

### Qdrant

Stores chunk vectors and retrieval payload metadata:

- `document_id`, `filename`, `chunk_id`, `chunk_index`
- owner and visibility metadata
- text/snippet payload
