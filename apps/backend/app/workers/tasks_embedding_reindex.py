from __future__ import annotations

from celery import shared_task

from app.db.session import SessionLocal
from app.services.embedding_reindex_service import EmbeddingReindexService


@shared_task(
    name="app.workers.tasks_embedding_reindex.run_embedding_reindex_run_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def run_embedding_reindex_run_task(self, run_id: str):  # noqa: ANN001
    with SessionLocal() as db:
        service = EmbeddingReindexService(db)
        try:
            result = service.run_reindex(run_id)
            db.commit()
            return result
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            raise self.retry(exc=exc)

