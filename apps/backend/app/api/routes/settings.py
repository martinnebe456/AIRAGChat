from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.models import User
from app.db.models.enums import RoleEnum
from app.db.session import get_db
from app.schemas.settings import (
    EmbeddingSettingsResponse,
    EmbeddingSettingsUpdateRequest,
    ModelSettingsResponse,
    ModelSettingsUpdateRequest,
    PublicClientSettingsResponse,
    SettingsNamespaceResponse,
    SettingsNamespaceUpdateRequest,
)
from app.services.audit_service import AuditService
from app.services.embedding_provider_service import EmbeddingProviderService
from app.services.settings_service import SettingsService

router = APIRouter()


def _to_resp(row) -> SettingsNamespaceResponse:  # noqa: ANN001
    return SettingsNamespaceResponse(
        namespace=row.namespace,
        key=row.key,
        value_json=row.value_json,
        version=row.version,
        updated_at=row.updated_at,
    )


@router.get("/rag", response_model=SettingsNamespaceResponse)
def get_rag_settings(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> SettingsNamespaceResponse:
    return _to_resp(SettingsService(db).get_namespace("rag", "defaults"))


@router.put("/rag", response_model=SettingsNamespaceResponse)
def put_rag_settings(
    payload: SettingsNamespaceUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> SettingsNamespaceResponse:
    row = SettingsService(db).update_namespace("rag", "defaults", payload.value_json, admin.id)
    db.commit()
    return _to_resp(row)


@router.get("/prompts", response_model=SettingsNamespaceResponse)
def get_prompt_settings(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> SettingsNamespaceResponse:
    return _to_resp(SettingsService(db).get_namespace("prompts", "chat"))


@router.put("/prompts", response_model=SettingsNamespaceResponse)
def put_prompt_settings(
    payload: SettingsNamespaceUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> SettingsNamespaceResponse:
    row = SettingsService(db).update_namespace("prompts", "chat", payload.value_json, admin.id)
    db.commit()
    return _to_resp(row)


@router.get("/evals-defaults", response_model=SettingsNamespaceResponse)
def get_eval_defaults(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> SettingsNamespaceResponse:
    return _to_resp(SettingsService(db).get_namespace("eval_defaults", "defaults"))


@router.put("/evals-defaults", response_model=SettingsNamespaceResponse)
def put_eval_defaults(
    payload: SettingsNamespaceUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> SettingsNamespaceResponse:
    row = SettingsService(db).update_namespace("eval_defaults", "defaults", payload.value_json, admin.id)
    db.commit()
    return _to_resp(row)


@router.get("/telemetry", response_model=SettingsNamespaceResponse)
def get_telemetry_settings(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> SettingsNamespaceResponse:
    return _to_resp(SettingsService(db).get_namespace("telemetry", "frontend"))


@router.put("/telemetry", response_model=SettingsNamespaceResponse)
def put_telemetry_settings(
    payload: SettingsNamespaceUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> SettingsNamespaceResponse:
    row = SettingsService(db).update_namespace("telemetry", "frontend", payload.value_json, admin.id)
    db.commit()
    return _to_resp(row)


@router.get("/models", response_model=ModelSettingsResponse)
def get_model_settings(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> ModelSettingsResponse:
    row = SettingsService(db).get_namespace("models", "defaults")
    return ModelSettingsResponse(
        namespace=row.namespace,
        key=row.key,
        value_json=dict(row.value_json or {}),
        version=row.version,
        updated_at=row.updated_at,
    )


@router.put("/models", response_model=ModelSettingsResponse)
def put_model_settings(
    payload: ModelSettingsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> ModelSettingsResponse:
    before = dict(SettingsService(db).get_namespace("models", "defaults").value_json or {})
    value_json = payload.model_dump()
    # Normalize required limits and keep values positive.
    pdf_limits = value_json.get("pdf_limits") or {}
    value_json["pdf_limits"] = {
        "max_upload_mb": max(1, int(pdf_limits.get("max_upload_mb", 100))),
        "max_pdf_pages": max(1, int(pdf_limits.get("max_pdf_pages", 1000))),
    }
    row = SettingsService(db).update_namespace("models", "defaults", value_json, admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="models.settings.update",
        entity_type="system_setting",
        entity_id=row.id,
        request=request,
        before_json=before,
        after_json=value_json,
    )
    db.commit()
    return ModelSettingsResponse(
        namespace=row.namespace,
        key=row.key,
        value_json=dict(row.value_json or {}),
        version=row.version,
        updated_at=row.updated_at,
    )


@router.get("/embeddings", response_model=EmbeddingSettingsResponse)
def get_embedding_settings(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingSettingsResponse:
    service = EmbeddingProviderService(db)
    row = service.get_settings_row()
    return EmbeddingSettingsResponse(
        namespace=row.namespace,
        key=row.key,
        value_json=dict(row.value_json or {}),
        version=row.version,
        updated_at=row.updated_at,
        active_profile=service.profile_to_dict(service.get_active_profile()),
        latest_draft_profile=service.profile_to_dict(service.get_latest_draft_profile()),
    )


@router.put("/embeddings", response_model=EmbeddingSettingsResponse)
def put_embedding_settings(
    payload: EmbeddingSettingsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EmbeddingSettingsResponse:
    service = EmbeddingProviderService(db)
    before = service.get_settings_value()
    result = service.update_embedding_settings(payload.model_dump(), admin.id)
    row = result["settings_row"]
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="embedding.settings.update",
        entity_type="system_setting",
        entity_id=row.id,
        request=request,
        before_json=before,
        after_json={
            "value_json": row.value_json,
            "latest_draft_profile_id": getattr(result.get("latest_draft_profile"), "id", None),
            "validation": {
                "provider": result["validation"].get("provider"),
                "model_id": result["validation"].get("model_id"),
                "dimensions": result["validation"].get("dimensions"),
                "warnings": result["validation"].get("warnings", []),
            },
        },
    )
    db.commit()
    return EmbeddingSettingsResponse(
        namespace=row.namespace,
        key=row.key,
        value_json=dict(row.value_json or {}),
        version=row.version,
        updated_at=row.updated_at,
        active_profile=service.profile_to_dict(result["active_profile"]),
        latest_draft_profile=service.profile_to_dict(result["latest_draft_profile"]),
    )


@router.get("/public-client", response_model=PublicClientSettingsResponse)
def public_client_settings(db: Session = Depends(get_db)) -> PublicClientSettingsResponse:
    row = SettingsService(db).get_namespace("telemetry", "frontend")
    value = row.value_json or {}
    return PublicClientSettingsResponse(
        frontend_telemetry_enabled=bool(value.get("enabled", True)),
        frontend_telemetry_sampling_rate=float(value.get("sampling_rate", 1.0)),
        log_level=str(value.get("log_level", "INFO")),
    )
