from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    EvaluationDataset,
    EvaluationDatasetItem,
    EvaluationMetricsSummary,
    EvaluationRun,
    EvaluationRunItem,
    Project,
    User,
)
from app.providers.evaluation.local_supplemental_metrics import compute_supplemental_metrics
from app.services.chat_service import ChatService
from app.services.provider_service import ProviderService


class EvaluationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_datasets(self) -> tuple[list[EvaluationDataset], int]:
        items = list(self.db.scalars(select(EvaluationDataset).order_by(EvaluationDataset.created_at.desc())).all())
        return items, len(items)

    def import_dataset(self, *, name: str, description: str | None, source_format: str, items: list[dict[str, Any]], created_by_user_id: str | None):
        ds = EvaluationDataset(
            name=name,
            description=description,
            source_format=source_format,
            status="active",
            item_count=len(items),
            created_by_user_id=created_by_user_id,
        )
        self.db.add(ds)
        self.db.flush()
        for idx, item in enumerate(items):
            self.db.add(
                EvaluationDatasetItem(
                    dataset_id=ds.id,
                    case_key=str(item.get("case_key") or f"case-{idx+1}"),
                    question=str(item.get("question") or ""),
                    expected_answer=item.get("expected_answer"),
                    expected_sources_json=item.get("expected_sources") or item.get("expected_sources_json"),
                    expects_refusal=bool(item.get("expects_refusal", False)),
                    metadata_json=item.get("metadata"),
                    tags_json=item.get("tags"),
                )
            )
        self.db.flush()
        return ds

    def get_dataset(self, dataset_id: str) -> EvaluationDataset:
        if dataset_id == "sample-default":
            row = self.db.scalar(
                select(EvaluationDataset).where(EvaluationDataset.name == "Sample Starter Dataset").limit(1)
            )
            if row:
                return row
        row = self.db.get(EvaluationDataset, dataset_id)
        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return row

    def list_dataset_items(self, dataset_id: str) -> tuple[list[EvaluationDatasetItem], int]:
        ds = self.get_dataset(dataset_id)
        items = list(
            self.db.scalars(
                select(EvaluationDatasetItem)
                .where(EvaluationDatasetItem.dataset_id == ds.id)
                .order_by(EvaluationDatasetItem.created_at.asc())
            ).all()
        )
        return items, len(items)

    def archive_dataset(self, dataset_id: str) -> EvaluationDataset:
        ds = self.get_dataset(dataset_id)
        ds.status = "archived"
        self.db.flush()
        return ds

    def create_run(
        self,
        *,
        dataset_id: str,
        provider: str,
        model_category: str,
        rag_overrides: dict[str, Any] | None,
        started_by_user_id: str | None,
    ) -> EvaluationRun:
        ds = self.get_dataset(dataset_id)
        provider_service = ProviderService(self.db)
        resolved_model_id = provider_service.resolve_chat_model()
        run = EvaluationRun(
            dataset_id=ds.id,
            dataset_version=ds.version,
            status="queued",
            provider="openai_api",
            model_category=model_category,
            resolved_model_id=resolved_model_id,
            config_snapshot_json={"rag_overrides": rag_overrides or {}},
            llama_stack_eval_used=False,
            started_by_user_id=started_by_user_id,
        )
        self.db.add(run)
        self.db.flush()
        from app.workers.celery_app import enqueue_eval_run

        enqueue_eval_run(run.id)
        return run

    def list_runs(self) -> tuple[list[EvaluationRun], int]:
        items = list(self.db.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc())).all())
        return items, len(items)

    def get_run(self, run_id: str) -> EvaluationRun:
        row = self.db.get(EvaluationRun, run_id)
        if not row:
            raise HTTPException(status_code=404, detail="Evaluation run not found")
        return row

    def list_run_items(self, run_id: str) -> tuple[list[EvaluationRunItem], int]:
        items = list(
            self.db.scalars(
                select(EvaluationRunItem)
                .where(EvaluationRunItem.run_id == run_id)
                .order_by(EvaluationRunItem.created_at.asc())
            ).all()
        )
        return items, len(items)

    def compare_runs(self, run_a_id: str, run_b_id: str) -> dict[str, Any]:
        run_a = self.get_run(run_a_id)
        run_b = self.get_run(run_b_id)
        a_summary = self.db.scalar(select(EvaluationMetricsSummary).where(EvaluationMetricsSummary.run_id == run_a.id).limit(1))
        b_summary = self.db.scalar(select(EvaluationMetricsSummary).where(EvaluationMetricsSummary.run_id == run_b.id).limit(1))
        a_metrics = (a_summary.metrics_json if a_summary else {}) or {}
        b_metrics = (b_summary.metrics_json if b_summary else {}) or {}
        deltas: dict[str, Any] = {}
        for key in set(a_metrics) | set(b_metrics):
            av = a_metrics.get(key)
            bv = b_metrics.get(key)
            if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
                deltas[key] = {"a": av, "b": bv, "delta": bv - av}
            else:
                deltas[key] = {"a": av, "b": bv}
        return {"run_a": run_a, "run_b": run_b, "deltas": deltas}

    def execute_run(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        if not run.dataset_id:
            raise ValueError("Evaluation run has no dataset")
        run.status = "running"
        run.started_at = datetime.now(UTC)
        self.db.flush()

        chat_service = ChatService(self.db)
        ds_items, _ = self.list_dataset_items(run.dataset_id)
        eval_user = self.db.get(User, run.started_by_user_id) if run.started_by_user_id else None
        if eval_user is None:
            raise HTTPException(status_code=400, detail="Evaluation run starter user not found")
        rag_overrides = (run.config_snapshot_json or {}).get("rag_overrides") if isinstance(run.config_snapshot_json, dict) else {}
        eval_project_id = rag_overrides.get("project_id") if isinstance(rag_overrides, dict) else None
        if not eval_project_id:
            first_project = self.db.scalar(
                select(Project).where(Project.is_active.is_(True)).order_by(Project.created_at.asc()).limit(1)
            )
            if not first_project:
                raise HTTPException(status_code=400, detail="No active project available for evaluation")
            eval_project_id = first_project.id
        result_rows: list[EvaluationRunItem] = []
        total_latency = 0
        success_count = 0
        hit_scores: list[float] = []
        refusal_scores: list[float] = []

        for item in ds_items:
            started = datetime.now(UTC)
            try:
                answer = chat_service.ask(
                    current_user=eval_user,
                    question=item.question,
                    session_id=None,
                    project_id=eval_project_id,
                    document_ids=None,
                    provider_override="openai_api",
                )
                retrieved_ids = [c["chunk_id"] for c in answer["citations"] if c.get("chunk_id")]
                supplemental = compute_supplemental_metrics(
                    expected_sources=list(item.expected_sources_json or []) if isinstance(item.expected_sources_json, list) else None,
                    retrieved_chunk_ids=retrieved_ids,
                    answer=answer["answer"],
                    citations_present=bool(answer["citations"]),
                    expects_refusal=item.expects_refusal,
                )
                metrics = {**supplemental, "llama_stack_summary": None}
                latency_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
                row = EvaluationRunItem(
                    run_id=run.id,
                    dataset_item_id=item.id,
                    status="completed",
                    question=item.question,
                    expected_answer_snapshot=item.expected_answer,
                    retrieved_chunks_json=answer["citations"],
                    answer_text=answer["answer"],
                    citations_json=answer["citations"],
                    metrics_json=metrics,
                    latency_ms=latency_ms,
                    token_usage_json=answer.get("usage"),
                    estimated_cost_usd=None,
                )
                self.db.add(row)
                result_rows.append(row)
                total_latency += latency_ms
                success_count += 1
                if isinstance(metrics.get("hit_at_k"), (int, float)):
                    hit_scores.append(float(metrics["hit_at_k"]))
                if isinstance(metrics.get("refusal_correctness"), (int, float)):
                    refusal_scores.append(float(metrics["refusal_correctness"]))
            except Exception as exc:  # noqa: BLE001
                row = EvaluationRunItem(
                    run_id=run.id,
                    dataset_item_id=item.id,
                    status="failed",
                    question=item.question,
                    expected_answer_snapshot=item.expected_answer,
                    error_details_json={"error": str(exc)},
                )
                self.db.add(row)
                result_rows.append(row)
        self.db.flush()

        summary = {
            "items_total": len(ds_items),
            "items_success": success_count,
            "items_failed": len(ds_items) - success_count,
            "error_rate": (len(ds_items) - success_count) / len(ds_items) if ds_items else 0.0,
            "avg_latency_ms": (total_latency / success_count) if success_count else None,
            "hit_at_k_avg": (sum(hit_scores) / len(hit_scores)) if hit_scores else None,
            "refusal_correctness_rate": (sum(refusal_scores) / len(refusal_scores)) if refusal_scores else None,
        }
        self.db.add(EvaluationMetricsSummary(run_id=run.id, metrics_json=summary))
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        self.db.flush()
        return summary
