from __future__ import annotations

from pydantic import BaseModel


class TelemetryStatusResponse(BaseModel):
    otel_enabled: bool
    collector_endpoint: str
    grafana_url: str
    jaeger_url: str
    prometheus_url: str
    loki_url: str

