from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.models.enums import DocumentStatusEnum, RoleEnum


class Document(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    filename_stored: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_ext: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[DocumentStatusEnum] = mapped_column(
        Enum(DocumentStatusEnum), nullable=False, default=DocumentStatusEnum.UPLOADED
    )
    status_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_details_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexed_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parser_metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    processing_progress_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    visibility_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="workspace")
    min_role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False, default=RoleEnum.USER)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentProcessingJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_processing_jobs"

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, default="ingest")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="queued")
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dispatch_trigger: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dispatch_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    progress_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DocumentProcessingJobEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_processing_job_events"

    job_id: Mapped[str] = mapped_column(ForeignKey("document_processing_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, default="info")
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
