from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Document, DocumentProcessingJob, DocumentProcessingJobEvent
from app.rag.chunking.recursive_chunker import chunk_text
from app.rag.parsers.document_parser import parse_document_content
from app.services.document_lock_service import DocumentLockService, DocumentLockUnavailableError
from app.services.embedding_provider_service import EmbeddingProviderService
from app.services.settings_service import SettingsService


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.embedding_provider_service = EmbeddingProviderService(db)
        self.document_lock_service = DocumentLockService()
        self.qdrant = QdrantClient(host=self.settings.qdrant_host, port=self.settings.qdrant_port)
        self.settings_service = SettingsService(db)

    def _effective_max_pdf_pages(self) -> int:
        try:
            row = self.settings_service.get_namespace("models", "defaults")
            value = row.value_json or {}
            pdf_limits = value.get("pdf_limits") or {}
            return max(1, int(pdf_limits.get("max_pdf_pages", self.settings.max_pdf_pages)))
        except Exception:  # noqa: BLE001
            return self.settings.max_pdf_pages

    def _log_event(self, job_id: str, stage: str, message: str, *, level: str = "info", details=None) -> None:  # noqa: ANN001
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

    def _update_job_progress(self, job: DocumentProcessingJob, **progress) -> None:  # noqa: ANN003
        current = {}
        if isinstance(job.progress_json, dict):
            current.update(job.progress_json)
        current.update(progress)
        job.progress_json = current
        self.db.flush()

    def _resolve_embedding_context(
        self,
        *,
        embedding_profile_id: str | None = None,
        target_collection_name: str | None = None,
    ):
        if embedding_profile_id:
            profile = self.embedding_provider_service.get_profile(embedding_profile_id)
        else:
            profile = self.embedding_provider_service.get_active_profile()
        provider = self.embedding_provider_service.provider_from_profile(profile)
        collection = target_collection_name or self.embedding_provider_service.get_active_collection_alias_or_name()
        return profile, provider, collection

    @staticmethod
    def _qdrant_point_id(document_id: str, chunk_id: str) -> str:
        # Qdrant accepts point IDs as UUID or unsigned integer. Use a deterministic UUID
        # derived from document/chunk identity so reindexing remains idempotent.
        return str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk_id}"))

    def ensure_collection(
        self,
        *,
        collection_name: str | None = None,
        embedding_profile_id: str | None = None,
    ) -> None:
        profile, provider, resolved_collection = self._resolve_embedding_context(
            embedding_profile_id=embedding_profile_id,
            target_collection_name=collection_name,
        )
        name = collection_name or resolved_collection
        dim = profile.dimensions or provider.dimension()
        alias_target = self.embedding_provider_service.get_alias_target(name)
        check_name = alias_target or name
        try:
            exists = self.qdrant.collection_exists(check_name)
        except Exception:  # noqa: BLE001
            exists = False
        if not exists:
            self.embedding_provider_service.ensure_collection(
                name,
                size=dim,
                distance_metric=profile.distance_metric,
            )

    def delete_document_vectors(self, document_id: str, *, collection_name: str | None = None) -> None:
        effective_collection = collection_name or self.embedding_provider_service.get_active_collection_alias_or_name()
        target_collection = self.embedding_provider_service.get_alias_target(effective_collection) or effective_collection
        try:
            exists = self.qdrant.collection_exists(target_collection)
        except Exception:  # noqa: BLE001
            exists = False
        if not exists:
            return
        self.qdrant.delete(
            collection_name=effective_collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=document_id))]
                )
            ),
        )

    def embed_document_to_collection(
        self,
        document: Document,
        *,
        job_id: str | None = None,
        embedding_profile_id: str | None = None,
        target_collection_name: str | None = None,
        update_document_status: bool = True,
    ) -> dict[str, Any]:
        profile, embedding_provider, collection_name = self._resolve_embedding_context(
            embedding_profile_id=embedding_profile_id,
            target_collection_name=target_collection_name,
        )
        write_collection_name = self.embedding_provider_service.get_alias_target(collection_name) or collection_name
        embedding_batch_size = max(
            1,
            int(getattr(embedding_provider, "batch_size", None) or self.settings.embedding_batch_size),
        )

        if update_document_status:
            document.status = "parsing"  # type: ignore[assignment]
            self.db.flush()
            document.processing_progress_json = {"stage": "parsing"}
        if job_id:
            self._log_event(job_id, "parsing", "Parsing document")
        parsed = parse_document_content(
            Path(document.storage_path),
            max_pdf_pages=self._effective_max_pdf_pages(),
            pdf_ocr_enabled=self.settings.pdf_ocr_enabled,
        )
        parser_meta = parsed.metadata if isinstance(parsed.metadata, dict) else {}
        document.page_count = parser_meta.get("pages") if isinstance(parser_meta, dict) else None
        document.parser_metadata_json = parser_meta
        if job_id:
            self._log_event(job_id, "normalization", "Normalized document text", details=parser_meta)
            if parser_meta.get("empty_pages"):
                self._log_event(
                    job_id,
                    "parsing",
                    "Some PDF pages had no extractable text",
                    level="warning",
                    details={"empty_pages": parser_meta.get("empty_pages"), "pages": parser_meta.get("pages")},
                )

        if update_document_status:
            document.status = "chunking"  # type: ignore[assignment]
            self.db.flush()
            document.processing_progress_json = {"stage": "chunking", "chunks_total": 0}

        total_pages = int(parser_meta.get("pages") or 0)
        sections = parsed.sections
        has_page_sections = any(section.source_page is not None for section in sections)
        job_for_progress = self.db.get(DocumentProcessingJob, job_id) if job_id else None
        chunks_total = 0
        embedded_chunks = 0
        indexed_chunks = 0
        global_chunk_index = 0
        chunk_batch: list[Any] = []  # TextChunk list
        collection_ensured = False

        def update_progress(stage: str, *, page_index: int | None = None) -> None:
            progress: dict[str, Any] = {
                "stage": stage,
                "chunks_total": chunks_total,
                "embedded_chunks": embedded_chunks,
                "indexed_chunks": indexed_chunks,
            }
            if total_pages:
                progress.update({"pages_total": total_pages})
            if page_index is not None:
                progress["pages_processed"] = page_index
            if update_document_status:
                document.processing_progress_json = progress
            if job_for_progress is not None:
                self._update_job_progress(job=job_for_progress, **progress)

        def flush_chunk_batch(page_index: int | None = None) -> None:
            nonlocal embedded_chunks, indexed_chunks, collection_ensured, chunk_batch
            if not chunk_batch:
                return
            if update_document_status:
                document.status = "embedding"  # type: ignore[assignment]
                self.db.flush()
            texts = [c.text for c in chunk_batch]
            vectors = embedding_provider.embed_texts(texts, input_kind="document")
            embedded_chunks += len(vectors.vectors)
            if job_id:
                self._log_event(
                    job_id,
                    "embedding",
                    "Generated embedding batch",
                    details={
                        "batch_size": len(chunk_batch),
                        "embedded_chunks": embedded_chunks,
                        "chunks_total": chunks_total,
                    },
                )
            if not collection_ensured:
                self.embedding_provider_service.ensure_collection(
                    write_collection_name,
                    size=profile.dimensions or vectors.dimension,
                    distance_metric=profile.distance_metric,
                )
                collection_ensured = True
            points: list[qmodels.PointStruct] = []
            for chunk, vector in zip(chunk_batch, vectors.vectors, strict=False):
                points.append(
                    qmodels.PointStruct(
                        id=self._qdrant_point_id(document.id, chunk.chunk_id),
                        vector=vector,
                        payload={
                            "document_id": document.id,
                            "project_id": getattr(document, "project_id", None),
                            "filename": document.filename_original,
                            "chunk_id": chunk.chunk_id,
                            "chunk_index": chunk.index,
                            "owner_user_id": document.owner_user_id,
                            "visibility_scope": document.visibility_scope,
                            "min_role": document.min_role.value if hasattr(document.min_role, "value") else str(document.min_role),
                            "created_at": document.created_at.isoformat() if document.created_at else None,
                            "source_page": getattr(chunk, "source_page", None),
                            "text": chunk.text,
                            "text_excerpt": chunk.text[:240],
                            "embedding_profile_id": profile.id,
                            "embedding_provider": profile.provider,
                            "embedding_model_id": profile.model_id,
                        },
                    )
                )
            if update_document_status:
                document.status = "embedding"  # type: ignore[assignment]
                self.db.flush()
            self.qdrant.upsert(collection_name=write_collection_name, points=points)
            indexed_chunks += len(points)
            if job_id:
                self._log_event(
                    job_id,
                    "indexing",
                    "Upserted vector batch",
                    details={
                        "batch_size": len(points),
                        "indexed_chunks": indexed_chunks,
                        "chunks_total": chunks_total,
                    },
                )
            chunk_batch = []
            update_progress("indexing", page_index=page_index)

        if update_document_status:
            document.status = "chunking"  # type: ignore[assignment]
            self.db.flush()

        empty_text_sections = 0
        for section_idx, section in enumerate(sections, start=1):
            normalized = " ".join((section.text or "").split())
            if not normalized:
                empty_text_sections += 1
                if has_page_sections:
                    update_progress("chunking", page_index=section_idx)
                continue
            new_chunks = chunk_text(
                document.id,
                normalized,
                chunk_size=self.settings.rag_chunk_size,
                chunk_overlap=self.settings.rag_chunk_overlap,
                start_index=global_chunk_index,
                source_page=section.source_page,
            )
            global_chunk_index += len(new_chunks)
            chunks_total += len(new_chunks)
            chunk_batch.extend(new_chunks)

            if job_id and (section_idx == 1 or section_idx == len(sections) or section_idx % 25 == 0):
                self._log_event(
                    job_id,
                    "chunking",
                    "Chunking progress",
                    details={
                        "sections_processed": section_idx,
                        "sections_total": len(sections),
                        "chunks_total": chunks_total,
                    },
                )
            update_progress("chunking", page_index=section_idx if has_page_sections else None)

            while len(chunk_batch) >= embedding_batch_size:
                if update_document_status:
                    document.status = "embedding"  # type: ignore[assignment]
                remainder = chunk_batch[embedding_batch_size:]
                chunk_batch = chunk_batch[:embedding_batch_size]
                flush_chunk_batch(page_index=section_idx if has_page_sections else None)
                chunk_batch = remainder

        if chunks_total == 0:
            if has_page_sections and total_pages > 0 and not self.settings.pdf_ocr_enabled:
                raise ValueError(
                    "No extractable text found in the PDF. It may be a scanned/image PDF and OCR is disabled."
                )
            raise ValueError("No extractable text found in the document")

        if update_document_status:
            document.chunk_count = chunks_total
            document.processing_progress_json = {
                "stage": "embedding" if chunk_batch else "indexing",
                "chunks_total": chunks_total,
                "embedded_chunks": embedded_chunks,
                "indexed_chunks": indexed_chunks,
                **({"pages_total": total_pages} if total_pages else {}),
                **({"empty_text_sections": empty_text_sections} if empty_text_sections else {}),
            }
            self.db.flush()
        if job_id:
            self._log_event(
                job_id,
                "chunking",
                f"Created {chunks_total} chunks",
                details={"empty_text_sections": empty_text_sections},
            )

        if chunk_batch:
            flush_chunk_batch(page_index=len(sections) if has_page_sections else None)

        if update_document_status:
            document.processing_progress_json = {
                "stage": "indexing",
                "chunks_total": chunks_total,
                "embedded_chunks": embedded_chunks,
                "indexed_chunks": indexed_chunks,
                **({"pages_total": total_pages} if total_pages else {}),
                **({"pages_processed": total_pages} if total_pages else {}),
                **({"empty_text_sections": empty_text_sections} if empty_text_sections else {}),
            }

        return {
            "collection_name": collection_name,
            "write_collection_name": write_collection_name,
            "embedding_profile_id": profile.id,
            "chunks": indexed_chunks,
            "parser_meta": parser_meta,
            "content_hash_snapshot": document.content_hash,
            "document_updated_at_snapshot": document.updated_at,
        }

    def run_ingestion_job(
        self,
        job_id: str,
        *,
        embedding_profile_id: str | None = None,
        target_collection_name: str | None = None,
        update_document_status: bool = True,
    ) -> dict[str, Any]:
        job = self.db.get(DocumentProcessingJob, job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        document = self.db.get(Document, job.document_id)
        if not document:
            raise ValueError(f"Document not found for job: {job_id}")

        try:
            job.attempt_count = int(job.attempt_count or 0) + 1
            if job.status != "running":
                job.status = "running"
            job.started_at = job.started_at or datetime.now(UTC)
            self._update_job_progress(job, stage="running")
            self._log_event(job.id, "dispatch", "Worker picked up job")
            with self.document_lock_service.lock(document.id, timeout_seconds=240, blocking_timeout_seconds=5):
                self.delete_document_vectors(document.id)
                if update_document_status:
                    document.status = "parsing"
                self.db.flush()
                result = self.embed_document_to_collection(
                    document,
                    job_id=job.id,
                    embedding_profile_id=embedding_profile_id,
                    target_collection_name=target_collection_name,
                    update_document_status=update_document_status,
                )
                if update_document_status:
                    document.status = "indexed"
                    document.status_message = "Indexed successfully"
                    document.indexed_chunk_count = int(result["chunks"])
                    prev_progress = (
                        dict(document.processing_progress_json)
                        if isinstance(document.processing_progress_json, dict)
                        else {}
                    )
                    document.processing_progress_json = {
                        **prev_progress,
                        "stage": "indexed",
                        "indexed_chunks": int(result["chunks"]),
                        "chunks_total": int(result["chunks"]),
                    }
                job.status = "succeeded"
                job.finished_at = datetime.now(UTC)
                self._update_job_progress(job, stage="indexed", indexed_chunks=int(result["chunks"]), chunks_total=int(result["chunks"]))
                self._log_event(job.id, "finalize", "Document indexed successfully")
                self.db.flush()
                return {"ok": True, "document_id": document.id, "job_id": job.id, "chunks": int(result["chunks"])}
        except DocumentLockUnavailableError as exc:
            if update_document_status:
                document.status = "uploaded"
                document.status_message = "Document is busy; retry scheduled"
            job.status = "queued"
            job.error_summary = str(exc)
            job.finished_at = None
            self._update_job_progress(job, stage="queued", retry_scheduled=True)
            self._log_event(
                job.id,
                "finalize",
                "Processing deferred because document is locked; job returned to queue",
                level="warning",
                details={"error": str(exc)},
            )
            self.db.flush()
            raise
        except Exception as exc:  # noqa: BLE001
            if update_document_status:
                document.status = "failed"
                document.status_message = "Processing failed"
                document.error_details_json = {"error": str(exc)}
                document.processing_progress_json = {"stage": "failed", "error": str(exc)}
            job.status = "failed"
            job.error_summary = str(exc)
            job.finished_at = datetime.now(UTC)
            self._update_job_progress(job, stage="failed", error=str(exc))
            self._log_event(job.id, "finalize", "Processing failed", level="error", details={"error": str(exc)})
            self.db.flush()
            raise

    def upsert_job(
        self,
        document_id: str,
        requested_by_user_id: str | None,
        job_type: str = "ingest",
        project_id: str | None = None,
    ) -> DocumentProcessingJob:
        job = DocumentProcessingJob(
            document_id=document_id,
            project_id=project_id,
            requested_by_user_id=requested_by_user_id,
            job_type=job_type,
            status="queued",
            attempt_count=0,
            progress_json={"stage": "queued"},
        )
        self.db.add(job)
        self.db.flush()
        self._log_event(job.id, "upload", "Job queued")
        return job

    def list_jobs(self, document_id: str | None = None) -> tuple[list[DocumentProcessingJob], int]:
        stmt = select(DocumentProcessingJob).order_by(DocumentProcessingJob.created_at.desc())
        if document_id:
            stmt = stmt.where(DocumentProcessingJob.document_id == document_id)
        items = list(self.db.scalars(stmt).all())
        return items, len(items)

    def get_job(self, job_id: str) -> DocumentProcessingJob | None:
        return self.db.get(DocumentProcessingJob, job_id)

    def list_jobs_filtered(
        self,
        *,
        project_id: str | None = None,
        statuses: set[str] | None = None,
        job_types: set[str] | None = None,
        limit: int | None = None,
        include_recent_completed_hours: int | None = None,
        document_id: str | None = None,
        accessible_project_ids: set[str] | None = None,
    ) -> tuple[list[DocumentProcessingJob], int]:
        stmt = select(DocumentProcessingJob)
        if project_id:
            stmt = stmt.where(DocumentProcessingJob.project_id == project_id)
        if accessible_project_ids is not None:
            if not accessible_project_ids:
                return [], 0
            stmt = stmt.where(DocumentProcessingJob.project_id.in_(accessible_project_ids))
        if document_id:
            stmt = stmt.where(DocumentProcessingJob.document_id == document_id)
        if statuses:
            stmt = stmt.where(DocumentProcessingJob.status.in_(sorted(statuses)))
        if job_types:
            stmt = stmt.where(DocumentProcessingJob.job_type.in_(sorted(job_types)))
        if include_recent_completed_hours and include_recent_completed_hours > 0:
            cutoff = datetime.now(UTC) - timedelta(hours=int(include_recent_completed_hours))
            terminal_statuses = {"succeeded", "failed", "cancelled", "skipped"}
            stmt = stmt.where(
                or_(
                    ~DocumentProcessingJob.status.in_(terminal_statuses),
                    DocumentProcessingJob.updated_at >= cutoff,
                )
            )
        stmt = stmt.order_by(DocumentProcessingJob.created_at.desc())
        if limit:
            stmt = stmt.limit(int(limit))
        items = list(self.db.scalars(stmt).all())
        return items, len(items)

    def list_job_events(self, job_id: str) -> tuple[list[DocumentProcessingJobEvent], int]:
        items = list(
            self.db.scalars(
                select(DocumentProcessingJobEvent)
                .where(DocumentProcessingJobEvent.job_id == job_id)
                .order_by(DocumentProcessingJobEvent.created_at.asc())
            ).all()
        )
        return items, len(items)
