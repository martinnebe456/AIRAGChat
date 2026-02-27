from __future__ import annotations

from celery import shared_task

from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService


@shared_task(name="app.workers.tasks_ingestion.run_ingestion_job_task", bind=True, max_retries=3, default_retry_delay=5)
def run_ingestion_job_task(self, job_id: str):  # noqa: ANN001
    with SessionLocal() as db:
        service = IngestionService(db)
        try:
            result = service.run_ingestion_job(job_id)
            db.commit()
            return result
        except Exception as exc:  # noqa: BLE001
            try:
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
            raise self.retry(exc=exc)
