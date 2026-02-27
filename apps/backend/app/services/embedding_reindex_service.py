from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, EmbeddingReindexRun, EmbeddingReindexRunItem
from app.services.document_lock_service import DocumentLockService, DocumentLockUnavailableError
from app.services.embedding_provider_service import EmbeddingProviderService
from app.services.ingestion_service import IngestionService


class EmbeddingReindexService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding_provider_service = EmbeddingProviderService(db)
        self.ingestion_service = IngestionService(db)
        self.document_lock_service = DocumentLockService()

    def _run_to_dict(self, row: EmbeddingReindexRun) -> dict[str, Any]:
        summary = row.summary_json or {}
        if isinstance(summary, list):
            summary = {"items": summary}
        return {
            "id": row.id,
            "target_embedding_profile_id": row.target_embedding_profile_id,
            "source_embedding_profile_id": row.source_embedding_profile_id,
            "status": row.status,
            "scope_json": row.scope_json or {},
            "qdrant_staging_collection": row.qdrant_staging_collection,
            "started_by_user_id": row.started_by_user_id,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "applied_by_user_id": row.applied_by_user_id,
            "applied_at": row.applied_at,
            "summary_json": summary,
            "drift_detected_count": row.drift_detected_count,
            "error_summary": row.error_summary,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _item_to_dict(self, row: EmbeddingReindexRunItem) -> dict[str, Any]:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "document_id": row.document_id,
            "status": row.status,
            "attempt_count": row.attempt_count,
            "document_content_hash_snapshot": row.document_content_hash_snapshot,
            "indexed_chunk_count": row.indexed_chunk_count,
            "error_summary": row.error_summary,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "last_seen_document_updated_at": row.last_seen_document_updated_at,
            "needs_catchup": row.needs_catchup,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _refresh_run_summary(self, run_id: str) -> dict[str, Any]:
        items = list(
            self.db.scalars(
                select(EmbeddingReindexRunItem).where(EmbeddingReindexRunItem.run_id == run_id)
            ).all()
        )
        by_status: dict[str, int] = {}
        for item in items:
            by_status[item.status] = by_status.get(item.status, 0) + 1
        summary = {
            "total": len(items),
            "by_status": by_status,
            "needs_catchup": sum(1 for i in items if i.needs_catchup),
            "indexed_chunks_total": sum(int(i.indexed_chunk_count or 0) for i in items),
        }
        run = self.get_run(run_id)
        run.summary_json = summary
        run.drift_detected_count = int(summary["needs_catchup"])
        self.db.flush()
        return summary

    def status(self) -> dict[str, Any]:
        return self.embedding_provider_service.status_payload()

    def list_runs(self) -> tuple[list[EmbeddingReindexRun], int]:
        rows = list(
            self.db.scalars(select(EmbeddingReindexRun).order_by(EmbeddingReindexRun.created_at.desc())).all()
        )
        return rows, len(rows)

    def get_run(self, run_id: str) -> EmbeddingReindexRun:
        row = self.db.get(EmbeddingReindexRun, run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Embedding reindex run not found")
        return row

    def list_run_items(self, run_id: str) -> tuple[list[EmbeddingReindexRunItem], int]:
        _ = self.get_run(run_id)
        rows = list(
            self.db.scalars(
                select(EmbeddingReindexRunItem)
                .where(EmbeddingReindexRunItem.run_id == run_id)
                .order_by(EmbeddingReindexRunItem.created_at.asc())
            ).all()
        )
        return rows, len(rows)

    def create_run(
        self,
        *,
        target_embedding_profile_id: str | None,
        use_latest_draft: bool,
        scope: dict[str, Any],
        actor_user_id: str | None,
    ) -> EmbeddingReindexRun:
        self.embedding_provider_service.ensure_bootstrap_state()
        target_profile = None
        if target_embedding_profile_id:
            target_profile = self.embedding_provider_service.get_profile(target_embedding_profile_id)
        elif use_latest_draft:
            target_profile = self.embedding_provider_service.get_latest_draft_profile()
        if target_profile is None:
            raise HTTPException(status_code=400, detail="No target embedding profile available")
        source_profile = self.embedding_provider_service.get_active_profile()
        if target_profile.id == source_profile.id:
            raise HTTPException(status_code=400, detail="Target profile is already active")

        staging_collection = f"documents_chunks__ep_{target_profile.id[:8]}__run_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        self.embedding_provider_service.ensure_collection(
            staging_collection,
            size=target_profile.dimensions,
            distance_metric=target_profile.distance_metric,
        )
        target_profile.qdrant_collection_name = staging_collection
        target_profile.updated_by_user_id = actor_user_id

        run = EmbeddingReindexRun(
            target_embedding_profile_id=target_profile.id,
            source_embedding_profile_id=source_profile.id,
            status="queued",
            scope_json=scope or {"kind": "all_documents"},
            qdrant_staging_collection=staging_collection,
            started_by_user_id=actor_user_id,
            summary_json={},
        )
        self.db.add(run)
        self.db.flush()

        docs = list(
            self.db.scalars(
                select(Document)
                .where(Document.deleted_at.is_(None))
                .order_by(Document.created_at.asc())
            ).all()
        )
        for doc in docs:
            self.db.add(
                EmbeddingReindexRunItem(
                    run_id=run.id,
                    document_id=doc.id,
                    status="queued",
                    attempt_count=0,
                    document_content_hash_snapshot=doc.content_hash,
                    indexed_chunk_count=0,
                    last_seen_document_updated_at=doc.updated_at,
                    needs_catchup=False,
                )
            )
        self.db.flush()
        self._refresh_run_summary(run.id)
        return run

    def enqueue_run(self, run_id: str) -> str:
        from app.workers.celery_app import enqueue_embedding_reindex_run

        return enqueue_embedding_reindex_run(run_id)

    def cancel_run(self, run_id: str) -> EmbeddingReindexRun:
        run = self.get_run(run_id)
        if run.status not in {"queued", "running", "catchup_pending", "catchup_running"}:
            raise HTTPException(status_code=400, detail="Run cannot be cancelled in current state")
        run.status = "cancelled"
        run.finished_at = datetime.now(UTC)
        self.db.flush()
        return run

    def _index_single_item(self, run: EmbeddingReindexRun, item: EmbeddingReindexRunItem) -> None:
        doc = self.db.get(Document, item.document_id)
        if doc is None or doc.deleted_at is not None:
            item.status = "skipped"
            item.error_summary = "Document no longer exists"
            item.finished_at = datetime.now(UTC)
            self.db.flush()
            return
        item.started_at = item.started_at or datetime.now(UTC)
        item.attempt_count = int(item.attempt_count or 0) + 1
        item.status = "running"
        self.db.flush()

        try:
            with self.document_lock_service.lock(doc.id, timeout_seconds=300, blocking_timeout_seconds=1):
                self.ingestion_service.delete_document_vectors(
                    doc.id,
                    collection_name=run.qdrant_staging_collection,
                )
                result = self.ingestion_service.embed_document_to_collection(
                    doc,
                    embedding_profile_id=run.target_embedding_profile_id,
                    target_collection_name=run.qdrant_staging_collection,
                    update_document_status=False,
                )
                item.indexed_chunk_count = int(result.get("chunks") or 0)
                changed = False
                if item.document_content_hash_snapshot and doc.content_hash and item.document_content_hash_snapshot != doc.content_hash:
                    changed = True
                if item.last_seen_document_updated_at and doc.updated_at and doc.updated_at > item.last_seen_document_updated_at:
                    changed = True
                item.needs_catchup = changed
                item.last_seen_document_updated_at = doc.updated_at
                item.status = "succeeded"
                item.error_summary = None
                item.finished_at = datetime.now(UTC)
                self.db.flush()
        except DocumentLockUnavailableError as exc:
            item.status = "locked"
            item.error_summary = str(exc)
            item.needs_catchup = True
            item.finished_at = datetime.now(UTC)
            self.db.flush()
        except Exception as exc:  # noqa: BLE001
            item.status = "failed"
            item.error_summary = str(exc)
            item.finished_at = datetime.now(UTC)
            self.db.flush()

    def run_reindex(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        if run.status in {"cancelled", "applied"}:
            return self._run_to_dict(run)
        run.status = "running"
        run.started_at = run.started_at or datetime.now(UTC)
        self.db.flush()

        items = list(
            self.db.scalars(
                select(EmbeddingReindexRunItem)
                .where(EmbeddingReindexRunItem.run_id == run.id)
                .order_by(EmbeddingReindexRunItem.created_at.asc())
            ).all()
        )
        for item in items:
            self.db.refresh(run)
            if run.status == "cancelled":
                break
            if item.status == "succeeded":
                continue
            self._index_single_item(run, item)

        summary = self._refresh_run_summary(run.id)
        has_failures = (summary.get("by_status", {}) or {}).get("failed", 0) > 0
        run.finished_at = datetime.now(UTC)
        if run.status != "cancelled":
            run.status = "failed" if has_failures else "apply_ready"
        self.db.flush()
        return self._run_to_dict(run)

    def catchup_preview(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        items = list(
            self.db.scalars(
                select(EmbeddingReindexRunItem).where(EmbeddingReindexRunItem.run_id == run.id)
            ).all()
        )
        stale_items: list[str] = []
        for item in items:
            doc = self.db.get(Document, item.document_id)
            if doc is None or doc.deleted_at is not None:
                continue
            if item.status in {"failed", "locked", "skipped"}:
                stale_items.append(item.id)
                continue
            if item.needs_catchup:
                stale_items.append(item.id)
                continue
            if item.document_content_hash_snapshot and doc.content_hash and item.document_content_hash_snapshot != doc.content_hash:
                stale_items.append(item.id)
                continue
            if item.last_seen_document_updated_at and doc.updated_at and doc.updated_at > item.last_seen_document_updated_at:
                stale_items.append(item.id)
                continue
        return {
            "run_id": run.id,
            "stale_item_count": len(stale_items),
            "stale_item_ids": stale_items[:50],
            "apply_blocked": run.status not in {"apply_ready", "completed", "failed"} and run.status != "catchup_pending",
        }

    def _run_catchup(self, run: EmbeddingReindexRun) -> dict[str, Any]:
        items = list(
            self.db.scalars(
                select(EmbeddingReindexRunItem)
                .where(EmbeddingReindexRunItem.run_id == run.id)
                .order_by(EmbeddingReindexRunItem.created_at.asc())
            ).all()
        )
        run.status = "catchup_running"
        self.db.flush()
        reprocessed = 0
        failed = 0
        for item in items:
            doc = self.db.get(Document, item.document_id)
            if doc is None or doc.deleted_at is not None:
                continue
            needs = item.needs_catchup or item.status in {"failed", "locked", "skipped"}
            if not needs:
                if item.document_content_hash_snapshot and doc.content_hash and item.document_content_hash_snapshot != doc.content_hash:
                    needs = True
                elif item.last_seen_document_updated_at and doc.updated_at and doc.updated_at > item.last_seen_document_updated_at:
                    needs = True
            if not needs:
                continue
            self._index_single_item(run, item)
            reprocessed += 1
            if item.status != "succeeded":
                failed += 1
        summary = self._refresh_run_summary(run.id)
        return {"reprocessed_items": reprocessed, "failed_items": failed, "summary": summary}

    def apply_run(self, run_id: str, *, actor_user_id: str | None) -> dict[str, Any]:
        run = self.get_run(run_id)
        if run.status not in {"apply_ready", "completed", "failed", "catchup_pending"}:
            raise HTTPException(status_code=400, detail="Run is not ready to apply")
        catchup_summary = self._run_catchup(run)
        summary = self._refresh_run_summary(run.id)
        if (summary.get("by_status", {}) or {}).get("failed", 0) > 0:
            run.status = "failed"
            run.error_summary = "Apply blocked because some items still failed after catch-up"
            self.db.flush()
            raise HTTPException(status_code=400, detail=run.error_summary)

        target_profile = self.embedding_provider_service.get_profile(run.target_embedding_profile_id)
        alias_name = target_profile.qdrant_alias_name or self.embedding_provider_service.get_active_alias_name()
        alias_target = self.embedding_provider_service.switch_alias(
            alias_name=alias_name,
            new_collection=run.qdrant_staging_collection,
        )
        target_profile.qdrant_collection_name = run.qdrant_staging_collection
        self.embedding_provider_service.mark_profile_active(profile=target_profile, actor_user_id=actor_user_id)

        run.status = "applied"
        run.applied_by_user_id = actor_user_id
        run.applied_at = datetime.now(UTC)
        run.finished_at = run.finished_at or datetime.now(UTC)
        self.db.flush()
        return {
            "run_id": run.id,
            "applied": True,
            "status": run.status,
            "active_alias_name": alias_name,
            "active_alias_target": alias_target,
            "catchup_summary": catchup_summary,
        }

    def run_to_response(self, row: EmbeddingReindexRun) -> dict[str, Any]:
        return self._run_to_dict(row)

    def item_to_response(self, row: EmbeddingReindexRunItem) -> dict[str, Any]:
        return self._item_to_dict(row)
