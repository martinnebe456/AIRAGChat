# Telemetry and Observability

## Goals

- Trace end-to-end flows (frontend -> backend -> retrieval -> provider call)
- Monitor performance and failure modes
- Debug ingestion and eval pipeline issues
- Observe queue throughput and chat latency

## Stack (Local Docker)

- OpenTelemetry Collector
- Jaeger (traces)
- Prometheus (metrics)
- Grafana (dashboards)
- Loki (logs)

## Backend / Worker Instrumentation (Current + Extension Points)

Current repository includes:

- OTel initialization hook (`app/core/telemetry.py`)
- Prometheus metrics endpoint (`/metrics`)
- metrics helpers (`app/telemetry/metrics.py`)
- structured JSON logging formatter
- custom span helper placeholder (`app/telemetry/spans.py`)

Recommended expansions:

- FastAPI automatic instrumentation
- SQLAlchemy, Redis, HTTPX instrumentation
- Celery worker instrumentation
- custom spans around parse/chunk/embed/index/retrieve/infer/eval

## Frontend Telemetry

The frontend includes a lightweight telemetry bootstrap hook and DB-backed/public settings endpoints for:

- enable/disable flag
- sampling rate
- log level

The implementation is intentionally minimal and can be expanded with richer OTel web instrumentation.

## Grafana / Prometheus / Jaeger

Starter provisioning files are included under:

- `infra/grafana/provisioning`
- `infra/grafana/dashboards`
- `infra/prometheus/prometheus.yml`
- `infra/otel/otel-collector-config.yaml`

## Windows Note (Promtail)

Promtail host-container log mounts can require environment-specific adjustments on Docker Desktop for Windows. The rest of the observability stack remains useful even if host log shipping is disabled or moved to a separate profile.

