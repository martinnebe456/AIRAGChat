from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger


def configure_telemetry(settings: Settings) -> None:
    logger = get_logger(__name__)
    if not settings.otel_enabled:
        logger.info("telemetry.disabled", extra={"event": "telemetry_disabled"})
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("telemetry.enabled", extra={"event": "telemetry_enabled"})
    except Exception as exc:  # noqa: BLE001
        logger.warning("telemetry.init_failed", extra={"event": "telemetry_init_failed"}, exc_info=exc)

