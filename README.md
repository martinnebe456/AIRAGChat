# AIRAGChat

Language: **English** | [Čeština](README-CS.md) | [Deutsch](README-DE.md)

Proof of Concept (PoC) for a self-service chatbot over company documents.

AIRAGChat is a local, self-hosted RAG application built for internal document Q&A workflows. It combines a React frontend, FastAPI backend, PostgreSQL + Qdrant storage, async ingestion workers, and optional observability tooling.

## PoC Scope

- Self-service chat experience over uploaded company documents
- Role-based access (`user`, `contributor`, `admin`) with JWT + refresh cookie auth
- Document ingestion pipeline (upload -> parse -> chunk -> embed -> index)
- RAG answers with citations and retrieval metadata
- Admin-configured OpenAI runtime (chat + embeddings), with backend-only secret handling
- Evaluation datasets and run comparison for quality/regression checks

Current runtime mode is OpenAI-only (`openai_api`).

## Architecture At A Glance

- `apps/frontend`: React SPA (auth, chat, documents, admin pages)
- `apps/backend`: FastAPI API, Celery workers, SQLAlchemy/Alembic, RAG services
- `postgres`: relational data (users, projects, docs, chats, settings, audit, evals)
- `qdrant`: vector index for document chunks
- `redis`: queue broker/result backend
- `otel-collector`, `jaeger`, `prometheus`, `grafana`, `loki`: optional observability profile

## Repository Layout

```text
AIRAGChat/
|- apps/
|  |- backend/                     # FastAPI app, workers, DB models/migrations, tests
|  `- frontend/                    # React + Vite SPA
|- infra/
|  |- compose/                     # Docker Compose files (dev + prod-like override)
|  |- grafana/                     # Dashboard and provisioning
|  |- loki/
|  |- otel/
|  |- prometheus/
|  `- promtail/
|- scripts/                        # PowerShell helper scripts for local lifecycle
|- docs/                           # Architecture, RAG, RBAC, telemetry, setup notes
|- samples/                        # Example document and evaluation dataset
|- data/
|  `- uploads/                     # Local uploaded files volume
|- .env.example                    # Local configuration template
`- README.md
```

## Tech Stack

- Frontend: React, TypeScript, Vite, React Router, Zustand, TanStack Query, Tailwind CSS
- Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Celery
- Data: PostgreSQL, Redis, Qdrant, local upload volume
- AI runtime: OpenAI API (chat + embeddings)
- Observability: OpenTelemetry, Jaeger, Prometheus, Grafana, Loki

## First-Time Setup and Run

### 1. Prerequisites

- Docker Desktop (running)
- PowerShell

### 2. Create local environment file

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Recommended before first run:

- Change bootstrap admin credentials in `.env`
- Keep `APP_SECRETS_MASTER_KEY` set (required for encrypted secret storage)

### 3. Build and start the stack

```powershell
./scripts/dev-build.ps1
./scripts/dev-start.ps1
./scripts/dev-health.ps1
```

### 4. Open the app

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

Default admin (from `.env`):

- Username: `admin`
- Password: `ChangeMe123!`
- Email: `admin@example.local`

### 5. Configure OpenAI in Admin

After login, go to `Admin -> System Settings` and configure:

- OpenAI API key
- Chat model
- Embedding model

The key is sent to backend only and encrypted at rest (`APP_SECRETS_MASTER_KEY`).

### 6. Upload documents and start chatting

- Create/select a project in Admin
- Upload files in Documents
- Wait for ingestion/indexing
- Ask questions in Chat and review citations

## Useful Dev Commands

- Build images: `./scripts/dev-build.ps1`
- Start stack: `./scripts/dev-start.ps1`
- Stop stack: `./scripts/dev-stop.ps1`
- Restart stack: `./scripts/dev-restart.ps1`
- Health checks: `./scripts/dev-health.ps1`
- Tail logs: `./scripts/dev-logs.ps1`
- Backend logs only: `./scripts/dev-logs.ps1 -Service backend`
- Rebuild without cache: `./scripts/dev-rebuild-clean.ps1`
- Trigger sample eval run: `./scripts/dev-eval-run.ps1`

Optional flags:

- `-NoObservability` to skip Grafana/Jaeger/Prometheus/Loki profile
- `-ProdLike` to run runtime targets (`infra/compose/compose.prod-like.yaml`)

`./scripts/dev-setup-models.ps1` is kept as a compatibility stub and does not install local models.

## Local Service URLs

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Grafana: `http://localhost:3000`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`

## Security Notes

- Browser does not store OpenAI secrets in local/session storage
- Provider calls are proxied by backend only
- OpenAI key is encrypted at rest in the database
- Admin operations (users/settings/docs/evals) are audit-logged

## Documentation

- `docs/local-development.md`
- `docs/architecture.md`
- `docs/rag-pipeline.md`
- `docs/rbac.md`
- `docs/provider-switching.md`
- `docs/secrets-management.md`
- `docs/telemetry-observability.md`
- `docs/evaluation-framework.md`

## Notes

- `data/uploads` is a local persistent volume for uploaded files; avoid committing sensitive company documents.
- Some docs describe broader design ideas; current runtime defaults are OpenAI-only.
