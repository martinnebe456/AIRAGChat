from __future__ import annotations

from celery import shared_task

from app.db.session import SessionLocal
from app.services.ingestion_scheduler_service import IngestionSchedulerService


@shared_task(name="app.workers.tasks_maintenance.noop")
def noop_task() -> dict[str, str]:
    return {"status": "ok"}


@shared_task(name="app.workers.tasks_maintenance.dispatch_midnight_queued_documents_task")
def dispatch_midnight_queued_documents_task() -> dict[str, object]:
    with SessionLocal() as db:
        service = IngestionSchedulerService(db)
        try:
            result = service.run_midnight_dispatch_if_due()
            db.commit()
            return result
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            return {"ok": False, "error": str(exc)}
