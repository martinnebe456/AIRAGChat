from __future__ import annotations

from datetime import UTC, datetime
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentProcessingJob, DocumentProcessingJobEvent, User
from app.db.models.enums import RoleEnum
from app.services.ingestion_service import IngestionService
from app.services.project_access_service import ProjectAccessService


ACTIVE_JOB_STATUSES = {"queued", "dispatched", "running"}
TERMINAL_JOB_STATUSES = {"succeeded", "failed", "cancelled", "skipped"}


class QueuedIngestionDispatchService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ingestion_service = IngestionService(db)
        self.project_access_service = ProjectAccessService(db)

    @staticmethod
    def _job_to_dict(job: DocumentProcessingJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "document_id": job.document_id,
            "project_id": job.project_id,
            "requested_by_user_id": job.requested_by_user_id,
            "status": job.status,
            "job_type": job.job_type,
            "celery_task_id": job.celery_task_id,
            "dispatched_at": job.dispatched_at,
            "dispatched_by_user_id": job.dispatched_by_user_id,
            "dispatch_trigger": job.dispatch_trigger,
            "dispatch_batch_id": job.dispatch_batch_id,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "error_summary": job.error_summary,
            "attempt_count": int(job.attempt_count or 0),
            "progress_json": job.progress_json,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    def _log_job_event(
        self,
        job_id: str,
        *,
        stage: str,
        message: str,
        level: str = "info",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.db.add(
            DocumentProcessingJobEvent(
                job_id=job_id,
                level=level,
                stage=stage,
                message=message,
                details_json=details,
            )
        )
        self.db.flush()

    def _job_access_filter_project_ids(self, *, current_user: User) -> set[str] | None:
        if current_user.role == RoleEnum.ADMIN:
            return None
        return self.project_access_service.list_accessible_project_ids(user=current_user, minimum_role="viewer")

    def list_jobs_for_user(
        self,
        *,
        current_user: User,
        project_id: str | None = None,
        statuses: set[str] | None = None,
        job_types: set[str] | None = None,
        limit: int | None = None,
        include_recent_completed_hours: int | None = None,
        document_id: str | None = None,
    ) -> tuple[list[DocumentProcessingJob], int]:
        accessible_project_ids = self._job_access_filter_project_ids(current_user=current_user)
        if project_id:
            self.project_access_service.require_project_role(
                project_id=project_id,
                user=current_user,
                minimum_role="viewer",
            )
        return self.ingestion_service.list_jobs_filtered(
            project_id=project_id,
            statuses=statuses,
            job_types=job_types,
            limit=limit,
            include_recent_completed_hours=include_recent_completed_hours,
            document_id=document_id,
            accessible_project_ids=accessible_project_ids,
        )

    def get_job_for_user(self, *, job_id: str, current_user: User) -> DocumentProcessingJob:
        job = self.ingestion_service.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if current_user.role != RoleEnum.ADMIN:
            if not job.project_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            self.project_access_service.require_project_role(
                project_id=job.project_id,
                user=current_user,
                minimum_role="viewer",
            )
        return job

    def list_job_events_for_user(
        self,
        *,
        job_id: str,
        current_user: User,
    ) -> tuple[list[DocumentProcessingJobEvent], int]:
        _ = self.get_job_for_user(job_id=job_id, current_user=current_user)
        return self.ingestion_service.list_job_events(job_id)

    def _latest_event_map(self, job_ids: list[str]) -> dict[str, DocumentProcessingJobEvent]:
        result: dict[str, DocumentProcessingJobEvent] = {}
        if not job_ids:
            return result
        events = list(
            self.db.scalars(
                select(DocumentProcessingJobEvent)
                .where(DocumentProcessingJobEvent.job_id.in_(job_ids))
                .order_by(DocumentProcessingJobEvent.created_at.desc())
            ).all()
        )
        for event in events:
            if event.job_id not in result:
                result[event.job_id] = event
        return result

    def _document_name_map(self, document_ids: list[str]) -> dict[str, str]:
        if not document_ids:
            return {}
        rows = list(
            self.db.execute(
                select(Document.id, Document.filename_original).where(Document.id.in_(document_ids))
            ).all()
        )
        return {row[0]: row[1] for row in rows}

    def _job_summary_dicts(self, jobs: list[DocumentProcessingJob]) -> list[dict[str, Any]]:
        if not jobs:
            return []
        job_ids = [j.id for j in jobs]
        document_ids = [j.document_id for j in jobs]
        latest_event = self._latest_event_map(job_ids)
        doc_names = self._document_name_map(document_ids)
        out: list[dict[str, Any]] = []
        for job in jobs:
            ev = latest_event.get(job.id)
            out.append(
                {
                    "job": self._job_to_dict(job),
                    "filename_original": doc_names.get(job.document_id),
                    "latest_event_stage": ev.stage if ev else None,
                    "latest_event_level": ev.level if ev else None,
                    "latest_event_message": ev.message if ev else None,
                }
            )
        return out

    def list_queue_overview(self, *, project_id: str, current_user: User) -> dict[str, Any]:
        self.project_access_service.require_project_role(project_id=project_id, user=current_user, minimum_role="viewer")
        active_jobs_all, _ = self.list_jobs_for_user(
            current_user=current_user,
            project_id=project_id,
            statuses={"queued", "dispatched", "running"},
            limit=500,
        )
        recent_jobs_all, _ = self.list_jobs_for_user(
            current_user=current_user,
            project_id=project_id,
            statuses={"succeeded", "failed"},
            include_recent_completed_hours=24,
            limit=500,
        )
        queued_count = sum(1 for j in active_jobs_all if j.status == "queued")
        dispatched_count = sum(1 for j in active_jobs_all if j.status == "dispatched")
        running_count = sum(1 for j in active_jobs_all if j.status == "running")
        succeeded_recent_count = sum(1 for j in recent_jobs_all if j.status == "succeeded")
        failed_recent_count = sum(1 for j in recent_jobs_all if j.status == "failed")
        return {
            "project_id": project_id,
            "queued_count": queued_count,
            "dispatched_count": dispatched_count,
            "running_count": running_count,
            "succeeded_recent_count": succeeded_recent_count,
            "failed_recent_count": failed_recent_count,
            "active_jobs": self._job_summary_dicts(active_jobs_all[:100]),
            "recent_jobs": self._job_summary_dicts(recent_jobs_all[:50]),
        }

    def dedupe_queued_jobs(self, jobs: list[DocumentProcessingJob]) -> tuple[list[DocumentProcessingJob], int]:
        """Keep newest queued job per document and cancel older duplicates."""
        kept: list[DocumentProcessingJob] = []
        seen_docs: set[str] = set()
        superseded = 0
        for job in jobs:
            if job.document_id in seen_docs:
                job.status = "cancelled"
                job.error_summary = "Superseded by a newer queued job for the same document"
                job.finished_at = datetime.now(UTC)
                if isinstance(job.progress_json, dict):
                    progress = dict(job.progress_json)
                else:
                    progress = {}
                progress.update({"stage": "cancelled", "reason": "superseded"})
                job.progress_json = progress
                self._log_job_event(
                    job.id,
                    stage="dispatch",
                    level="warning",
                    message="Queued job cancelled as duplicate of a newer queued job",
                )
                superseded += 1
                continue
            seen_docs.add(job.document_id)
            kept.append(job)
        return kept, superseded

    def _active_document_ids(self, *, project_id: str | None) -> set[str]:
        stmt = select(DocumentProcessingJob.document_id).where(DocumentProcessingJob.status.in_({"dispatched", "running"}))
        if project_id:
            stmt = stmt.where(DocumentProcessingJob.project_id == project_id)
        rows = self.db.scalars(stmt).all()
        return set(rows)

    def _queued_jobs_scope(self, *, project_id: str | None) -> list[DocumentProcessingJob]:
        stmt = (
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.status == "queued")
            .order_by(DocumentProcessingJob.created_at.desc())
        )
        if project_id:
            stmt = stmt.where(DocumentProcessingJob.project_id == project_id)
        return list(self.db.scalars(stmt).all())

    def _queued_remaining_count(self, *, project_id: str | None) -> int:
        stmt = select(DocumentProcessingJob).where(DocumentProcessingJob.status == "queued")
        if project_id:
            stmt = stmt.where(DocumentProcessingJob.project_id == project_id)
        return len(list(self.db.scalars(stmt).all()))

    def _dispatch_jobs(
        self,
        *,
        jobs: list[DocumentProcessingJob],
        actor_user_id: str | None,
        trigger: str,
        project_id: str | None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        from app.workers.celery_app import enqueue_ingestion_job

        batch_dispatch_id = uuid.uuid4().hex[:16]
        jobs, superseded_count = self.dedupe_queued_jobs(jobs)
        if limit:
            jobs = jobs[: int(limit)]

        active_docs = self._active_document_ids(project_id=project_id)
        dispatchable: list[DocumentProcessingJob] = []
        already_running_count = 0
        for job in jobs:
            if job.document_id in active_docs:
                already_running_count += 1
                continue
            dispatchable.append(job)

        now = datetime.now(UTC)
        for job in dispatchable:
            job.status = "dispatched"
            job.dispatched_at = now
            job.dispatched_by_user_id = actor_user_id
            job.dispatch_trigger = trigger
            job.dispatch_batch_id = batch_dispatch_id
            job.error_summary = None
            if isinstance(job.progress_json, dict):
                progress = dict(job.progress_json)
            else:
                progress = {}
            progress.update({"stage": "dispatched", "dispatch_trigger": trigger})
            job.progress_json = progress
            self._log_job_event(
                job.id,
                stage="dispatch",
                message="Job dispatched to ingestion worker queue",
                details={"trigger": trigger, "batch_dispatch_id": batch_dispatch_id},
            )

        # Commit dispatch state before enqueue so workers can observe rows reliably.
        self.db.commit()

        dispatched_job_ids: list[str] = []
        for job in dispatchable:
            try:
                task_id = enqueue_ingestion_job(job.id)
                job.celery_task_id = task_id
                dispatched_job_ids.append(job.id)
            except Exception as exc:  # noqa: BLE001
                job.status = "queued"
                job.dispatched_at = None
                job.dispatched_by_user_id = None
                job.dispatch_trigger = None
                job.dispatch_batch_id = None
                job.error_summary = f"Dispatch failed, job returned to queue: {exc}"
                if isinstance(job.progress_json, dict):
                    progress = dict(job.progress_json)
                else:
                    progress = {}
                progress.update({"stage": "queued", "dispatch_error": str(exc)})
                job.progress_json = progress
                self._log_job_event(
                    job.id,
                    stage="dispatch",
                    level="error",
                    message="Failed to enqueue job; returned to queue",
                    details={"error": str(exc)},
                )
        self.db.commit()

        return {
            "project_id": project_id,
            "dispatched_count": len(dispatched_job_ids),
            "skipped_count": superseded_count,
            "already_running_count": already_running_count,
            "queued_remaining_count": self._queued_remaining_count(project_id=project_id),
            "batch_dispatch_id": batch_dispatch_id,
            "job_ids": dispatched_job_ids[:100],
        }

    def dispatch_queued_for_project(
        self,
        *,
        project_id: str,
        actor_user_id: str | None,
        trigger: str = "manual_admin",
        limit: int | None = None,
    ) -> dict[str, Any]:
        self.project_access_service.get_project(project_id)
        jobs = self._queued_jobs_scope(project_id=project_id)
        result = self._dispatch_jobs(
            jobs=jobs,
            actor_user_id=actor_user_id,
            trigger=trigger,
            project_id=project_id,
            limit=limit,
        )
        result["project_id"] = project_id
        return result

    def dispatch_queued_global(
        self,
        *,
        trigger: str,
        actor_user_id: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        jobs = self._queued_jobs_scope(project_id=None)
        result = self._dispatch_jobs(
            jobs=jobs,
            actor_user_id=actor_user_id,
            trigger=trigger,
            project_id=None,
            limit=limit,
        )
        result["project_id"] = "global"
        return result
