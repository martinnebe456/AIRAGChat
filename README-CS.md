# AIRAGChat

Jazyk: [English](README.md) | **Čeština** | [Deutsch](README-DE.md)

Proof of Concept (PoC) self-service chatbota nad firemními dokumenty.

AIRAGChat je lokální, self-hosted RAG aplikace určená pro interní Q&A workflow nad dokumenty. Kombinuje React frontend, FastAPI backend, úložiště PostgreSQL + Qdrant, asynchronní ingestion workery a volitelné observability nástroje.

## Rozsah PoC

- Self-service chat nad nahranými firemními dokumenty
- Role-based access (`user`, `contributor`, `admin`) s JWT + refresh cookie autentizací
- Ingestion pipeline dokumentů (upload -> parse -> chunk -> embed -> index)
- RAG odpovědi s citacemi a retrieval metadaty
- Admin konfigurace OpenAI runtime (chat + embeddings), s backend-only správou secretů
- Eval datasety a porovnání běhů pro kontrolu kvality/regresí

Aktuální runtime režim je pouze OpenAI (`openai_api`).

## Architektura V Kostce

- `apps/frontend`: React SPA (auth, chat, dokumenty, admin stránky)
- `apps/backend`: FastAPI API, Celery workery, SQLAlchemy/Alembic, RAG služby
- `postgres`: relační data (uživatelé, projekty, dokumenty, chaty, nastavení, audit, evals)
- `qdrant`: vektorový index chunků dokumentů
- `redis`: queue broker/result backend
- `otel-collector`, `jaeger`, `prometheus`, `grafana`, `loki`: volitelný observability profil

## Struktura Repozitáře

```text
AIRAGChat/
|- apps/
|  |- backend/                     # FastAPI app, workery, DB modely/migrace, testy
|  `- frontend/                    # React + Vite SPA
|- infra/
|  |- compose/                     # Docker Compose soubory (dev + prod-like override)
|  |- grafana/                     # Dashboardy a provisioning
|  |- loki/
|  |- otel/
|  |- prometheus/
|  `- promtail/
|- scripts/                        # PowerShell helper skripty pro lokální lifecycle
|- docs/                           # Architektura, RAG, RBAC, telemetry, setup poznámky
|- samples/                        # Ukázkový dokument a eval dataset
|- data/
|  `- uploads/                     # Lokální volume pro nahrané soubory
|- .env.example                    # Template lokální konfigurace
`- README-CS.md
```

## Tech Stack

- Frontend: React, TypeScript, Vite, React Router, Zustand, TanStack Query, Tailwind CSS
- Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Celery
- Data: PostgreSQL, Redis, Qdrant, lokální upload volume
- AI runtime: OpenAI API (chat + embeddings)
- Observability: OpenTelemetry, Jaeger, Prometheus, Grafana, Loki

## První Setup a Spuštění

### 1. Prerekvizity

- Docker Desktop (spuštěný)
- PowerShell

### 2. Vytvoření lokálního environment souboru

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Doporučeno před prvním spuštěním:

- Změňte bootstrap admin credentials v `.env`
- Ponechte nastavené `APP_SECRETS_MASTER_KEY` (nutné pro šifrované ukládání secretů)

### 3. Build a start stacku

```powershell
./scripts/dev-build.ps1
./scripts/dev-start.ps1
./scripts/dev-health.ps1
```

### 4. Otevření aplikace

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

Výchozí admin (z `.env`):

- Username: `admin`
- Password: `ChangeMe123!`
- Email: `admin@example.local`

### 5. Konfigurace OpenAI v Adminu

Po přihlášení přejděte do `Admin -> System Settings` a nastavte:

- OpenAI API key
- Chat model
- Embedding model

Klíč je posílán pouze na backend a je šifrován v klidu (`APP_SECRETS_MASTER_KEY`).

### 6. Nahrání dokumentů a spuštění chatu

- Vytvořte/vyberte projekt v Adminu
- Nahrajte soubory v Documents
- Počkejte na ingestion/indexaci
- Pokládejte dotazy v Chat a kontrolujte citace

## Užitečné Dev Příkazy

- Build image: `./scripts/dev-build.ps1`
- Start stacku: `./scripts/dev-start.ps1`
- Stop stacku: `./scripts/dev-stop.ps1`
- Restart stacku: `./scripts/dev-restart.ps1`
- Health checky: `./scripts/dev-health.ps1`
- Tail logů: `./scripts/dev-logs.ps1`
- Pouze backend logy: `./scripts/dev-logs.ps1 -Service backend`
- Rebuild bez cache: `./scripts/dev-rebuild-clean.ps1`
- Spuštění ukázkového eval běhu: `./scripts/dev-eval-run.ps1`

Volitelné přepínače:

- `-NoObservability` pro vypnutí Grafana/Jaeger/Prometheus/Loki profilu
- `-ProdLike` pro runtime targety (`infra/compose/compose.prod-like.yaml`)

`./scripts/dev-setup-models.ps1` je ponechán jako compatibility stub a neinstaluje lokální modely.

## Lokální URL Služeb

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Grafana: `http://localhost:3000`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`

## Bezpečnostní Poznámky

- Prohlížeč neukládá OpenAI secrets do local/session storage
- Provider volání jsou proxyována pouze přes backend
- OpenAI key je v databázi šifrován v klidu
- Admin operace (users/settings/docs/evals) jsou audit-logované

## Dokumentace

- `docs/local-development.md`
- `docs/architecture.md`
- `docs/rag-pipeline.md`
- `docs/rbac.md`
- `docs/provider-switching.md`
- `docs/secrets-management.md`
- `docs/telemetry-observability.md`
- `docs/evaluation-framework.md`
- `docs/business-case-cs.md` (česky)

## Poznámky

- `data/uploads` je lokální persistent volume pro nahrané soubory; necommitujte citlivé firemní dokumenty.
- Některé dokumenty popisují širší návrhové varianty; aktuální runtime default je OpenAI-only.
