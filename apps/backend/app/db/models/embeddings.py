from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class EmbeddingProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "embedding_profiles"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_metric: Mapped[str] = mapped_column(String(32), nullable=False, default="cosine")
    normalize_embeddings: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    input_prefix_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="e5")
    qdrant_collection_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qdrant_alias_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default="documents_chunks_active")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    validation_status_json: Mapped[dict | list] = mapped_column(JSON, nullable=False, default=dict)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    updated_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )


class EmbeddingReindexRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "embedding_reindex_runs"

    target_embedding_profile_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_embedding_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("embedding_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    scope_json: Mapped[dict | list] = mapped_column(JSON, nullable=False, default=dict)
    qdrant_staging_collection: Mapped[str] = mapped_column(String(255), nullable=False)
    started_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[dict | list] = mapped_column(JSON, nullable=False, default=dict)
    drift_detected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class EmbeddingReindexRunItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "embedding_reindex_run_items"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_reindex_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    document_content_hash_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    indexed_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_document_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    needs_catchup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processing_log_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

