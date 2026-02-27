# AIRAGChat

Sprache: [English](README.md) | [Čeština](README-CS.md) | **Deutsch**

Proof of Concept (PoC) fuer einen Self-Service-Chatbot ueber Unternehmensdokumente.

AIRAGChat ist eine lokale, self-hosted RAG-Anwendung fuer interne Q&A-Workflows auf Dokumentenbasis. Die Loesung kombiniert ein React-Frontend, ein FastAPI-Backend, PostgreSQL + Qdrant als Speicher, asynchrone Ingestion-Worker und optionales Observability-Tooling.

## PoC-Umfang

- Self-Service-Chat ueber hochgeladene Unternehmensdokumente
- Rollenbasierter Zugriff (`user`, `contributor`, `admin`) mit JWT + Refresh-Cookie-Authentifizierung
- Dokument-Ingestion-Pipeline (upload -> parse -> chunk -> embed -> index)
- RAG-Antworten mit Zitaten und Retrieval-Metadaten
- Admin-konfigurierter OpenAI-Runtime-Modus (Chat + Embeddings) mit backend-only Secret-Handling
- Eval-Datensaetze und Run-Vergleich zur Qualitaets- und Regressionskontrolle

Aktueller Runtime-Modus ist OpenAI-only (`openai_api`).

## Architektur Im Ueberblick

- `apps/frontend`: React SPA (Auth, Chat, Dokumente, Admin-Seiten)
- `apps/backend`: FastAPI API, Celery-Worker, SQLAlchemy/Alembic, RAG-Services
- `postgres`: relationale Daten (User, Projekte, Dokumente, Chats, Einstellungen, Audit, Evals)
- `qdrant`: Vektorindex fuer Dokument-Chunks
- `redis`: Queue-Broker/Result-Backend
- `otel-collector`, `jaeger`, `prometheus`, `grafana`, `loki`: optionales Observability-Profil

## Repository-Struktur

```text
AIRAGChat/
|- apps/
|  |- backend/                     # FastAPI-App, Worker, DB-Modelle/Migrationen, Tests
|  `- frontend/                    # React + Vite SPA
|- infra/
|  |- compose/                     # Docker-Compose-Dateien (dev + prod-like override)
|  |- grafana/                     # Dashboards und Provisioning
|  |- loki/
|  |- otel/
|  |- prometheus/
|  `- promtail/
|- scripts/                        # PowerShell-Helferskripte fuer lokalen Lifecycle
|- docs/                           # Architektur, RAG, RBAC, Telemetry, Setup-Hinweise
|- samples/                        # Beispieldokument und Eval-Datensatz
|- data/
|  `- uploads/                     # Lokales Volume fuer hochgeladene Dateien
|- .env.example                    # Vorlage fuer lokale Konfiguration
`- README-DE.md
```

## Tech Stack

- Frontend: React, TypeScript, Vite, React Router, Zustand, TanStack Query, Tailwind CSS
- Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Celery
- Daten: PostgreSQL, Redis, Qdrant, lokales Upload-Volume
- AI-Runtime: OpenAI API (Chat + Embeddings)
- Observability: OpenTelemetry, Jaeger, Prometheus, Grafana, Loki

## Erstes Setup und Start

### 1. Voraussetzungen

- Docker Desktop (laufend)
- PowerShell

### 2. Lokale Environment-Datei erstellen

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Empfohlen vor dem ersten Start:

- Bootstrap-Admin-Zugangsdaten in `.env` aendern
- `APP_SECRETS_MASTER_KEY` gesetzt lassen (erforderlich fuer verschluesselte Secret-Speicherung)

### 3. Build und Start des Stacks

```powershell
./scripts/dev-build.ps1
./scripts/dev-start.ps1
./scripts/dev-health.ps1
```

### 4. Anwendung aufrufen

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

Standard-Admin (aus `.env`):

- Username: `admin`
- Password: `ChangeMe123!`
- Email: `admin@example.local`

### 5. OpenAI im Admin-Bereich konfigurieren

Nach dem Login in `Admin -> System Settings` konfigurieren:

- OpenAI API key
- Chat model
- Embedding model

Der Schluessel wird nur ans Backend gesendet und at-rest verschluesselt gespeichert (`APP_SECRETS_MASTER_KEY`).

### 6. Dokumente hochladen und Chat starten

- Projekt im Admin-Bereich erstellen/auswaehlen
- Dateien in Documents hochladen
- Auf Ingestion/Indexierung warten
- Fragen im Chat stellen und Zitate pruefen

## Nuetzliche Dev-Befehle

- Images bauen: `./scripts/dev-build.ps1`
- Stack starten: `./scripts/dev-start.ps1`
- Stack stoppen: `./scripts/dev-stop.ps1`
- Stack neu starten: `./scripts/dev-restart.ps1`
- Health Checks: `./scripts/dev-health.ps1`
- Logs verfolgen: `./scripts/dev-logs.ps1`
- Nur Backend-Logs: `./scripts/dev-logs.ps1 -Service backend`
- Rebuild ohne Cache: `./scripts/dev-rebuild-clean.ps1`
- Beispiel-Eval-Run starten: `./scripts/dev-eval-run.ps1`

Optionale Flags:

- `-NoObservability` zum Deaktivieren des Grafana/Jaeger/Prometheus/Loki-Profils
- `-ProdLike` fuer Runtime-Targets (`infra/compose/compose.prod-like.yaml`)

`./scripts/dev-setup-models.ps1` bleibt als Kompatibilitaets-Stub erhalten und installiert keine lokalen Modelle.

## Lokale Service-URLs

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Grafana: `http://localhost:3000`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`

## Sicherheitshinweise

- Der Browser speichert keine OpenAI-Secrets in Local/Session Storage
- Provider-Aufrufe laufen ausschliesslich ueber das Backend
- OpenAI-Key wird in der Datenbank at-rest verschluesselt
- Admin-Aktionen (users/settings/docs/evals) werden audit-geloggt

## Dokumentation

- `docs/local-development.md`
- `docs/architecture.md`
- `docs/rag-pipeline.md`
- `docs/rbac.md`
- `docs/provider-switching.md`
- `docs/secrets-management.md`
- `docs/telemetry-observability.md`
- `docs/evaluation-framework.md`
- `docs/business-case-cs.md` (Tschechisch)

## Hinweise

- `data/uploads` ist ein lokales persistentes Volume fuer hochgeladene Dateien; sensible Unternehmensdokumente nicht committen.
- Einige Dokumente beschreiben breitere Architekturvarianten; aktueller Runtime-Default ist OpenAI-only.
