from __future__ import annotations

import hashlib
from pathlib import Path
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document, DocumentProcessingJob, User
from app.db.models.enums import DocumentStatusEnum, RoleEnum
from app.services.document_lock_service import DocumentLockService, DocumentLockUnavailableError
from app.services.ingestion_service import IngestionService
from app.services.project_access_service import ProjectAccessService
from app.services.settings_service import SettingsService


ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.document_lock_service = DocumentLockService()
        self.project_access_service = ProjectAccessService(db)
        self.settings_service = SettingsService(db)

    def _effective_max_upload_size_mb(self) -> int:
        try:
            row = self.settings_service.get_namespace("models", "defaults")
            value = row.value_json or {}
            pdf_limits = value.get("pdf_limits") or {}
            return max(1, int(pdf_limits.get("max_upload_mb", self.settings.max_upload_size_mb)))
        except Exception:  # noqa: BLE001
            return self.settings.max_upload_size_mb

    def _validate_upload(self, file: UploadFile) -> str:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        return suffix

    def _save_upload(self, file: UploadFile, suffix: str) -> tuple[Path, int, str]:
        self.settings.uploads_path.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        full_path = self.settings.uploads_path / stored_name
        hasher = hashlib.sha256()
        total_size = 0
        chunk_size = 1024 * 1024 * 2
        max_upload_mb = self._effective_max_upload_size_mb()
        limit_bytes = max_upload_mb * 1024 * 1024
        try:
            with full_path.open("wb") as out:
                while True:
                    chunk = file.file.read(chunk_size)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > limit_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds max size of {max_upload_mb}MB",
                        )
                    hasher.update(chunk)
                    out.write(chunk)
        except Exception:
            full_path.unlink(missing_ok=True)
            raise
        content_hash = hasher.hexdigest()
        return full_path, total_size, content_hash

    def _find_active_processing_job(self, document_id: str) -> DocumentProcessingJob | None:
        return self.db.scalar(
            select(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.document_id == document_id,
                DocumentProcessingJob.status.in_(("queued", "dispatched", "running")),
            )
            .order_by(DocumentProcessingJob.created_at.desc())
            .limit(1)
        )

    def upload_document(self, *, current_user: User, project_id: str, file: UploadFile):
        self.project_access_service.require_project_role(
            project_id=project_id,
            user=current_user,
            minimum_role="contributor",
        )
        suffix = self._validate_upload(file)
        path, size_bytes, content_hash = self._save_upload(file, suffix)

        document = Document(
            owner_user_id=current_user.id,
            project_id=project_id,
            filename_original=file.filename or path.name,
            filename_stored=path.name,
            file_ext=suffix,
            mime_type=file.content_type or "application/octet-stream",
            file_size_bytes=size_bytes,
            storage_path=str(path),
            status=DocumentStatusEnum.UPLOADED,
            status_message="Queued for processing",
            content_hash=content_hash,
            processing_progress_json={"stage": "queued"},
        )
        self.db.add(document)
        self.db.flush()

        ingestion = IngestionService(self.db)
        job = ingestion.upsert_job(document.id, current_user.id, job_type="ingest", project_id=project_id)
        self.db.flush()
        return document, job

    def list_documents(self, *, current_user: User, project_id: str | None = None) -> tuple[list[Document], int]:
        stmt = select(Document).where(Document.deleted_at.is_(None)).order_by(Document.created_at.desc())
        if project_id:
            self.project_access_service.require_project_role(project_id=project_id, user=current_user, minimum_role="viewer")
            stmt = stmt.where(Document.project_id == project_id)
        elif current_user.role != RoleEnum.ADMIN:
            project_ids = self.project_access_service.list_accessible_project_ids(user=current_user, minimum_role="viewer")
            if not project_ids:
                return [], 0
            stmt = stmt.where(Document.project_id.in_(project_ids))
        items = list(self.db.scalars(stmt).all())
        return items, len(items)

    def get_document(self, document_id: str, *, current_user: User) -> Document:
        doc = self.db.get(Document, document_id)
        if not doc or doc.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Document not found")
        if not doc.project_id:
            if current_user.role != RoleEnum.ADMIN and doc.owner_user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Forbidden")
            return doc
        self.project_access_service.require_project_role(project_id=doc.project_id, user=current_user, minimum_role="viewer")
        return doc

    def update_document(self, document_id: str, *, current_user: User, filename_original: str | None, archive: bool | None) -> Document:
        doc = self.get_document(document_id, current_user=current_user)
        if doc.project_id:
            self.project_access_service.require_project_role(project_id=doc.project_id, user=current_user, minimum_role="contributor")
        if filename_original:
            doc.filename_original = filename_original
        if archive is True:
            doc.status = DocumentStatusEnum.ARCHIVED
        self.db.flush()
        return doc

    def reprocess_document(self, document_id: str, *, current_user: User) -> tuple[DocumentProcessingJob, bool]:
        doc = self.get_document(document_id, current_user=current_user)
        if doc.project_id:
            self.project_access_service.require_project_role(project_id=doc.project_id, user=current_user, minimum_role="contributor")
        existing = self._find_active_processing_job(doc.id)
        if existing is not None:
            return existing, True

        ingestion = IngestionService(self.db)
        doc.status = DocumentStatusEnum.UPLOADED
        doc.status_message = "Queued for reprocess"
        doc.processing_progress_json = {"stage": "queued"}
        job = ingestion.upsert_job(doc.id, current_user.id, job_type="reprocess", project_id=doc.project_id)
        self.db.flush()
        return job, False

    def delete_document(
        self,
        document_id: str,
        *,
        current_user: User,
        delete_file: bool,
    ) -> tuple[Document, bool]:
        doc = self.get_document(document_id, current_user=current_user)
        if doc.project_id:
            self.project_access_service.require_project_role(project_id=doc.project_id, user=current_user, minimum_role="contributor")
        try:
            with self.document_lock_service.lock(doc.id, timeout_seconds=120, blocking_timeout_seconds=1):
                IngestionService(self.db).delete_document_vectors(doc.id)
                deleted_file = False
                if delete_file:
                    try:
                        Path(doc.storage_path).unlink(missing_ok=True)
                        deleted_file = True
                    except Exception:  # noqa: BLE001
                        deleted_file = False
                doc.deleted_at = doc.deleted_at or doc.updated_at
                self.db.delete(doc)
                self.db.flush()
                return doc, deleted_file
        except DocumentLockUnavailableError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
