from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.documents import (
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    ProcessingJobEventListResponse,
    ProcessingJobEventResponse,
    ProcessingJobResponse,
    ReprocessDocumentResponse,
)
from app.services.audit_service import AuditService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter()


def _doc_response(doc) -> DocumentResponse:  # noqa: ANN001
    return DocumentResponse(
        id=doc.id,
        owner_user_id=doc.owner_user_id,
        project_id=getattr(doc, "project_id", None),
        project_name=None,
        filename_original=doc.filename_original,
        file_ext=doc.file_ext,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        status_message=doc.status_message,
        chunk_count=doc.chunk_count,
        indexed_chunk_count=doc.indexed_chunk_count,
        page_count=getattr(doc, "page_count", None),
        processing_progress=getattr(doc, "processing_progress_json", None),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


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


@router.get("", response_model=DocumentListResponse)
def list_documents(
    project_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    items, total = DocumentService(db).list_documents(
        current_user=current_user,
        project_id=project_id,
    )
    return DocumentListResponse(items=[_doc_response(i) for i in items], total=total)


@router.post("/upload")
def upload_document(
    request: Request,
    project_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc, job = DocumentService(db).upload_document(
        current_user=current_user,
        project_id=project_id,
        file=file,
    )
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="document.upload",
        entity_type="document",
        entity_id=doc.id,
        after_json={"filename": doc.filename_original},
        request=request,
    )
    db.commit()
    return {"document": _doc_response(doc), "job": _job_response(job)}


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    doc = DocumentService(db).get_document(
        document_id,
        current_user=current_user,
    )
    return _doc_response(doc)


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    payload: DocumentUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    doc = DocumentService(db).update_document(
        document_id,
        current_user=current_user,
        filename_original=payload.filename_original,
        archive=payload.archive,
    )
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="document.update",
        entity_type="document",
        entity_id=doc.id,
        request=request,
    )
    db.commit()
    return _doc_response(doc)


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
def delete_document(
    document_id: str,
    request: Request,
    delete_file: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeleteDocumentResponse:
    doc, deleted_file = DocumentService(db).delete_document(
        document_id,
        current_user=current_user,
        delete_file=delete_file,
    )
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="document.delete",
        entity_type="document",
        entity_id=document_id,
        request=request,
        after_json={"delete_file": delete_file},
    )
    db.commit()
    return DeleteDocumentResponse(id=doc.id, deleted=True, deleted_file=deleted_file)


@router.post("/{document_id}/reprocess", response_model=ReprocessDocumentResponse)
def reprocess_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReprocessDocumentResponse:
    job, already_queued = DocumentService(db).reprocess_document(
        document_id,
        current_user=current_user,
    )
    AuditService(db).log(
        actor_user_id=current_user.id,
        action_type="document.reprocess",
        entity_type="document",
        entity_id=document_id,
        request=request,
    )
    db.commit()
    return ReprocessDocumentResponse(
        document_id=document_id,
        job_id=job.id,
        status=job.status,
        progress_json=getattr(job, "progress_json", None),
        queue_message="Already queued or running" if already_queued else "Queued for daily/manual processing",
        already_queued=already_queued,
    )


@router.get("/{document_id}/processing-status", response_model=ProcessingJobResponse)
def processing_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessingJobResponse:
    _ = DocumentService(db).get_document(document_id, current_user=current_user)
    jobs, _count = IngestionService(db).list_jobs(document_id=document_id)
    if not jobs:
        raise HTTPException(status_code=404, detail="No processing job found for document")
    return _job_response(jobs[0])


@router.get("/{document_id}/processing-logs", response_model=ProcessingJobEventListResponse)
def processing_logs(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessingJobEventListResponse:
    _ = DocumentService(db).get_document(document_id, current_user=current_user)
    jobs, _count = IngestionService(db).list_jobs(document_id=document_id)
    if not jobs:
        return ProcessingJobEventListResponse(items=[], total=0)
    events, total = IngestionService(db).list_job_events(jobs[0].id)
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
