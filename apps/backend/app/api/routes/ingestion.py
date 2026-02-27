from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.models import User
from app.db.models.enums import RoleEnum
from app.db.session import get_db
from app.schemas.documents import (
    ProcessingJobEventListResponse,
    ProcessingJobEventResponse,
    ProcessingJobListResponse,
    ProcessingJobResponse,
    QueueDispatchRequest,
    QueueDispatchResponse,
    QueueOverviewResponse,
    QueueSchedulerStatusResponse,
)
from app.services.audit_service import AuditService
from app.services.ingestion_scheduler_service import IngestionSchedulerService
from app.services.queued_ingestion_dispatch_service import QueuedIngestionDispatchService

router = APIRouter()


def _parse_csv_set(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    values = {v.strip() for v in raw.split(",") if v.strip()}
    return values or None


def _job_response(job) -> ProcessingJobResponse:  # noqa: ANN001
    return ProcessingJobResponse(
        id=job.id,
        document_id=job.document_id,
        project_id=getattr(job, "project_id", None),
        requested_by_user_id=getattr(job, "requested_by_user_id", None),
        status=job.status,
        job_type=job.job_type,
        celery_task_id=job.celery_task_id,
        dispatched_at=getattr(job, "dispatched_at", None),
        dispatched_by_user_id=getattr(job, "dispatched_by_user_id", None),
        dispatch_trigger=getattr(job, "dispatch_trigger", None),
        dispatch_batch_id=getattr(job, "dispatch_batch_id", None),
        started_at=getattr(job, "started_at", None),
        finished_at=getattr(job, "finished_at", None),
        error_summary=job.error_summary,
        attempt_count=job.attempt_count,
        progress_json=getattr(job, "progress_json", None),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs", response_model=ProcessingJobListResponse)
def list_jobs(
    project_id: str | None = Query(default=None),
    statuses: str | None = Query(default=None, description="CSV list, e.g. queued,dispatched,running"),
    job_types: str | None = Query(default=None, description="CSV list, e.g. ingest,reprocess"),
    limit: int | None = Query(default=50, ge=1, le=500),
    include_recent_completed_hours: int | None = Query(default=24, ge=0, le=720),
    document_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessingJobListResponse:
    service = QueuedIngestionDispatchService(db)
    jobs, total = service.list_jobs_for_user(
        current_user=current_user,
        project_id=project_id,
        statuses=_parse_csv_set(statuses),
        job_types=_parse_csv_set(job_types),
        limit=limit,
        include_recent_completed_hours=include_recent_completed_hours,
        document_id=document_id,
    )
    return ProcessingJobListResponse(items=[_job_response(j) for j in jobs], total=total)


@router.get("/jobs/{job_id}/events", response_model=ProcessingJobEventListResponse)
def get_job_events(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessingJobEventListResponse:
    service = QueuedIngestionDispatchService(db)
    events, total = service.list_job_events_for_user(job_id=job_id, current_user=current_user)
    return ProcessingJobEventListResponse(
        items=[
            ProcessingJobEventResponse(
                id=e.id,
                job_id=e.job_id,
                level=e.level,
                stage=e.stage,
                message=e.message,
                details_json=e.details_json,
                created_at=e.created_at,
            )
            for e in events
        ],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessingJobResponse:
    job = QueuedIngestionDispatchService(db).get_job_for_user(job_id=job_id, current_user=current_user)
    return _job_response(job)


@router.get("/queue/overview", response_model=QueueOverviewResponse)
def queue_overview(
    project_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueueOverviewResponse:
    dispatch_service = QueuedIngestionDispatchService(db)
    scheduler_service = IngestionSchedulerService(db)
    payload = dispatch_service.list_queue_overview(project_id=project_id, current_user=current_user)
    payload["scheduler_state"] = scheduler_service.get_scheduler_status()
    return QueueOverviewResponse(**payload)


@router.post("/queue/dispatch", response_model=QueueDispatchResponse)
def dispatch_queue_for_project(
    payload: QueueDispatchRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> QueueDispatchResponse:
    if not payload.queued_only:
        raise HTTPException(status_code=400, detail="Only queued_only=true is supported")
    service = QueuedIngestionDispatchService(db)
    result = service.dispatch_queued_for_project(
        project_id=payload.project_id,
        actor_user_id=current_user.id,
        trigger="manual_admin",
        limit=payload.limit,
    )
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="document.queue.dispatch",
        entity_type="project",
        entity_id=payload.project_id,
        request=request,
        after_json={
            "batch_dispatch_id": result.get("batch_dispatch_id"),
            "dispatched_count": result.get("dispatched_count"),
            "queued_remaining_count": result.get("queued_remaining_count"),
        },
    )
    db.commit()
    return QueueDispatchResponse(**result)


@router.get("/queue/scheduler-status", response_model=QueueSchedulerStatusResponse)
def queue_scheduler_status(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> QueueSchedulerStatusResponse:
    payload = IngestionSchedulerService(db).get_scheduler_status()
    return QueueSchedulerStatusResponse(**payload)
