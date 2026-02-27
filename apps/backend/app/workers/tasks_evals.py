from __future__ import annotations

from celery import shared_task

from app.db.session import SessionLocal
from app.services.evaluation_service import EvaluationService


@shared_task(name="app.workers.tasks_evals.run_eval_task", bind=True, max_retries=1, default_retry_delay=5)
def run_eval_task(self, run_id: str):  # noqa: ANN001
    with SessionLocal() as db:
        service = EvaluationService(db)
        try:
            result = service.execute_run(run_id)
            db.commit()
            return result
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            raise self.retry(exc=exc)

