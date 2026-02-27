from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "airagchat",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks_ingestion",
        "app.workers.tasks_evals",
        "app.workers.tasks_maintenance",
        "app.workers.tasks_embedding_reindex",
    ],
)
celery_app.conf.task_default_queue = "default"
celery_app.conf.timezone = "Europe/Prague"
celery_app.conf.enable_utc = True
celery_app.conf.task_routes = {
    "app.workers.tasks_ingestion.run_ingestion_job_task": {"queue": "ingestion"},
    "app.workers.tasks_evals.run_eval_task": {"queue": "evals"},
    "app.workers.tasks_embedding_reindex.run_embedding_reindex_run_task": {"queue": "ingestion"},
    "app.workers.tasks_maintenance.dispatch_midnight_queued_documents_task": {"queue": "default"},
}
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.beat_schedule = {
    "dispatch-midnight-queued-documents": {
        "task": "app.workers.tasks_maintenance.dispatch_midnight_queued_documents_task",
        "schedule": crontab(minute=0, hour=0),
    },
}


def enqueue_ingestion_job(job_id: str) -> str:
    result = celery_app.send_task("app.workers.tasks_ingestion.run_ingestion_job_task", args=[job_id], queue="ingestion")
    return str(result.id)


def enqueue_eval_run(run_id: str) -> str:
    result = celery_app.send_task("app.workers.tasks_evals.run_eval_task", args=[run_id], queue="evals")
    return str(result.id)


def enqueue_embedding_reindex_run(run_id: str) -> str:
    result = celery_app.send_task(
        "app.workers.tasks_embedding_reindex.run_embedding_reindex_run_task",
        args=[run_id],
        queue="ingestion",
    )
    return str(result.id)
