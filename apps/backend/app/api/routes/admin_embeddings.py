from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.models import User
from app.db.models.enums import RoleEnum
from app.db.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.settings import (
    EmbeddingProviderValidateRequest,
    EmbeddingProviderValidateResponse,
    EmbeddingReindexApplyResponse,
    EmbeddingReindexRunCreateRequest,
    EmbeddingReindexRunItemListResponse,
    EmbeddingReindexRunListResponse,
    EmbeddingReindexRunResponse,
    EmbeddingStatusResponse,
)
from app.services.audit_service import AuditService
from app.services.embedding_provider_service import EmbeddingProviderService
from app.services.embedding_reindex_service import EmbeddingReindexService

router = APIRouter()


@router.get("/status", response_model=EmbeddingStatusResponse)
def embedding_status(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingStatusResponse:
    return EmbeddingStatusResponse(**EmbeddingReindexService(db).status())


@router.post("/validate", response_model=EmbeddingProviderValidateResponse)
def validate_embedding_provider(
    payload: EmbeddingProviderValidateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingProviderValidateResponse:
    result = EmbeddingProviderService(db).validate_embedding_config(payload.model_dump())
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="embedding.profile.validate",
        entity_type="embedding_profile",
        request=request,
        after_json={"provider": payload.provider, "model_id": payload.model_id, "dimensions": result.get("dimensions")},
    )
    db.commit()
    return EmbeddingProviderValidateResponse(**{k: result[k] for k in ["ok", "provider", "model_id", "dimensions", "detail", "warnings", "metadata"]})


@router.post("/reindex-runs", response_model=EmbeddingReindexRunResponse)
def create_reindex_run(
    payload: EmbeddingReindexRunCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingReindexRunResponse:
    service = EmbeddingReindexService(db)
    run = service.create_run(
        target_embedding_profile_id=payload.target_embedding_profile_id,
        use_latest_draft=payload.use_latest_draft,
        scope=payload.scope,
        actor_user_id=admin.id,
    )
    task_id = service.enqueue_run(run.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="embedding.reindex.start",
        entity_type="embedding_reindex_run",
        entity_id=run.id,
        request=request,
        after_json={"task_id": task_id, "target_embedding_profile_id": run.target_embedding_profile_id},
    )
    db.commit()
    return EmbeddingReindexRunResponse(**service.run_to_response(run))


@router.get("/reindex-runs", response_model=EmbeddingReindexRunListResponse)
def list_reindex_runs(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingReindexRunListResponse:
    service = EmbeddingReindexService(db)
    rows, total = service.list_runs()
    return EmbeddingReindexRunListResponse(items=[EmbeddingReindexRunResponse(**service.run_to_response(r)) for r in rows], total=total)


@router.get("/reindex-runs/{run_id}", response_model=EmbeddingReindexRunResponse)
def get_reindex_run(
    run_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingReindexRunResponse:
    service = EmbeddingReindexService(db)
    row = service.get_run(run_id)
    return EmbeddingReindexRunResponse(**service.run_to_response(row))


@router.get("/reindex-runs/{run_id}/items", response_model=EmbeddingReindexRunItemListResponse)
def get_reindex_run_items(
    run_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingReindexRunItemListResponse:
    service = EmbeddingReindexService(db)
    rows, total = service.list_run_items(run_id)
    return EmbeddingReindexRunItemListResponse(
        items=[service.item_to_response(r) for r in rows],
        total=total,
    )


@router.post("/reindex-runs/{run_id}/catch-up-preview")
def catchup_preview(
    run_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> dict:
    return EmbeddingReindexService(db).catchup_preview(run_id)


@router.post("/reindex-runs/{run_id}/apply", response_model=EmbeddingReindexApplyResponse)
def apply_reindex_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingReindexApplyResponse:
    service = EmbeddingReindexService(db)
    result = service.apply_run(run_id, actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="embedding.reindex.apply",
        entity_type="embedding_reindex_run",
        entity_id=run_id,
        request=request,
        after_json=result,
    )
    db.commit()
    return EmbeddingReindexApplyResponse(**result)


@router.post("/reindex-runs/{run_id}/cancel", response_model=MessageResponse)
def cancel_reindex_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> MessageResponse:
    service = EmbeddingReindexService(db)
    run = service.cancel_run(run_id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="embedding.reindex.cancel",
        entity_type="embedding_reindex_run",
        entity_id=run.id,
        request=request,
        after_json={"status": run.status},
    )
    db.commit()
    return MessageResponse(message="Embedding reindex run cancelled")

