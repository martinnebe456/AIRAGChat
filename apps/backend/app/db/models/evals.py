from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class EvaluationDataset(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_datasets"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_format: Mapped[str] = mapped_column(String(32), nullable=False, default="json")
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class EvaluationDatasetItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_dataset_items"

    dataset_id: Mapped[str] = mapped_column(ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    case_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_sources_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    expects_refusal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    tags_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)


class EvaluationRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_runs"

    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("evaluation_datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    dataset_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_category: Mapped[str] = mapped_column(String(16), nullable=False)
    resolved_model_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    llama_stack_eval_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class EvaluationRunItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_run_items"

    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_item_id: Mapped[str | None] = mapped_column(ForeignKey("evaluation_dataset_items.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_chunks_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    metrics_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    error_details_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class EvaluationMetricsSummary(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_metrics_summary"

    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    comparison_baseline_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ModelUsageLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "model_usage_logs"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    context_type: Mapped[str] = mapped_column(String(32), nullable=False)
    context_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    model_category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)

