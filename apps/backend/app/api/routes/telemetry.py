from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.core.config import get_settings
from app.db.models import User
from app.db.models.enums import RoleEnum
from app.db.session import get_db
from app.schemas.telemetry import TelemetryStatusResponse

router = APIRouter()


@router.get("/status", response_model=TelemetryStatusResponse)
def telemetry_status(
    _db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> TelemetryStatusResponse:
    settings = get_settings()
    return TelemetryStatusResponse(
        otel_enabled=settings.otel_enabled,
        collector_endpoint=settings.otel_exporter_otlp_endpoint,
        grafana_url="http://localhost:3000",
        jaeger_url="http://localhost:16686",
        prometheus_url="http://localhost:9090",
        loki_url="http://localhost:3100",
    )


@router.get("/links")
def telemetry_links(
    _db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> dict:
    return {
        "grafana": "http://localhost:3000",
        "jaeger": "http://localhost:16686",
        "prometheus": "http://localhost:9090",
        "loki": "http://localhost:3100",
    }

