from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: str
    owner_user_id: str
    project_id: str | None = None
    project_name: str | None = None
    filename_original: str
    file_ext: str
    mime_type: str
    file_size_bytes: int
    status: str
    status_message: str | None = None
    chunk_count: int
    indexed_chunk_count: int
    page_count: int | None = None
    processing_progress: dict[str, Any] | list[Any] | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class DocumentUpdateRequest(BaseModel):
    filename_original: str | None = None
    archive: bool | None = None


class DeleteDocumentResponse(BaseModel):
    id: str
    deleted: bool
    deleted_file: bool


class ReprocessDocumentResponse(BaseModel):
    document_id: str
    job_id: str
    status: str
    progress_json: dict[str, Any] | list[Any] | None = None
    queue_message: str | None = None
    already_queued: bool = False


class ProcessingJobResponse(BaseModel):
    id: str
    document_id: str
    project_id: str | None = None
    requested_by_user_id: str | None = None
    status: str
    job_type: str
    celery_task_id: str | None = None
    dispatched_at: datetime | None = None
    dispatched_by_user_id: str | None = None
    dispatch_trigger: str | None = None
    dispatch_batch_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_summary: str | None = None
    attempt_count: int
    progress_json: dict[str, Any] | list[Any] | None = None
    created_at: datetime
    updated_at: datetime


class ProcessingJobListResponse(BaseModel):
    items: list[ProcessingJobResponse]
    total: int


class ProcessingJobEventResponse(BaseModel):
    id: str
    job_id: str
    level: str
    stage: str
    message: str
    details_json: dict[str, Any] | list[Any] | None = None
    created_at: datetime


class ProcessingJobEventListResponse(BaseModel):
    items: list[ProcessingJobEventResponse]
    total: int


class QueueJobSummaryResponse(BaseModel):
    job: ProcessingJobResponse
    filename_original: str | None = None
    latest_event_stage: str | None = None
    latest_event_level: str | None = None
    latest_event_message: str | None = None


class QueueSchedulerStatusResponse(BaseModel):
    timezone: str
    last_midnight_run_local_date: str | None = None
    last_midnight_dispatch_at: datetime | None = None
    last_midnight_dispatched_count: int = 0
    missed_run_detected: bool = False
    last_startup_catchup_at: datetime | None = None
    last_startup_catchup_dispatched_count: int = 0
    next_midnight_at_utc: datetime | None = None


class QueueOverviewResponse(BaseModel):
    project_id: str
    queued_count: int = 0
    dispatched_count: int = 0
    running_count: int = 0
    succeeded_recent_count: int = 0
    failed_recent_count: int = 0
    active_jobs: list[QueueJobSummaryResponse] = Field(default_factory=list)
    recent_jobs: list[QueueJobSummaryResponse] = Field(default_factory=list)
    scheduler_state: QueueSchedulerStatusResponse


class QueueDispatchRequest(BaseModel):
    project_id: str
    limit: int | None = Field(default=None, ge=1, le=500)
    queued_only: bool = True


class QueueDispatchResponse(BaseModel):
    project_id: str
    dispatched_count: int
    skipped_count: int
    already_running_count: int
    queued_remaining_count: int
    batch_dispatch_id: str
    job_ids: list[str] = Field(default_factory=list)
