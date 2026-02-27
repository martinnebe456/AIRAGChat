from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.models import User
from app.db.models.enums import RoleEnum
from app.db.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.settings import (
    OpenAIKeySetRequest,
    OpenAIKeyStatusResponse,
    OpenAIKeyTestRequest,
    ProviderModelMappingsUpdateRequest,
    ProviderStatusResponse,
    ProviderSwitchRequest,
)
from app.services.audit_service import AuditService
from app.services.provider_service import ProviderService

router = APIRouter()


@router.get("/status", response_model=ProviderStatusResponse)
def provider_status(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> ProviderStatusResponse:
    return ProviderStatusResponse(**ProviderService(db).get_provider_status())


@router.post("/switch")
def switch_provider(
    payload: ProviderSwitchRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> dict:
    result = ProviderService(db).switch_provider(provider=payload.provider, actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="provider.switch",
        entity_type="provider_settings",
        after_json=result,
        request=request,
    )
    db.commit()
    return result


@router.get("/model-mappings")
def get_model_mappings(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> dict:
    status = ProviderService(db).get_provider_status()
    return {"model_mappings": status["model_mappings"]}


@router.put("/model-mappings")
def put_model_mappings(
    payload: ProviderModelMappingsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> dict:
    mappings = ProviderService(db).update_model_mappings(mappings=payload.model_mappings, actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="provider.model_mappings.update",
        entity_type="provider_settings",
        after_json=mappings,
        request=request,
    )
    db.commit()
    return {"model_mappings": mappings}


@router.get("/openai/key-status", response_model=OpenAIKeyStatusResponse)
def openai_key_status(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> OpenAIKeyStatusResponse:
    return OpenAIKeyStatusResponse(**ProviderService(db).openai_key_status())


@router.put("/openai/key", response_model=OpenAIKeyStatusResponse)
def set_openai_key(
    payload: OpenAIKeySetRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> OpenAIKeyStatusResponse:
    status = ProviderService(db).set_openai_key(api_key=payload.api_key, actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="provider.openai_key.set",
        entity_type="secret",
        entity_id="openai_api_key",
        request=request,
    )
    db.commit()
    return OpenAIKeyStatusResponse(**status)


@router.post("/openai/key/test")
def test_openai_key(
    payload: OpenAIKeyTestRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> dict:
    result = ProviderService(db).test_openai_key(candidate_key=payload.api_key)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="provider.openai_key.test",
        entity_type="secret",
        entity_id="openai_api_key",
        request=request,
        after_json=result,
    )
    db.commit()
    return result


@router.post("/openai/key/rotate", response_model=OpenAIKeyStatusResponse)
def rotate_openai_key(
    payload: OpenAIKeySetRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> OpenAIKeyStatusResponse:
    status = ProviderService(db).rotate_openai_key(api_key=payload.api_key, actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="provider.openai_key.rotate",
        entity_type="secret",
        entity_id="openai_api_key",
        request=request,
    )
    db.commit()
    return OpenAIKeyStatusResponse(**status)


@router.delete("/openai/key")
def delete_openai_key(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> MessageResponse:
    ProviderService(db).remove_openai_key(actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="provider.openai_key.delete",
        entity_type="secret",
        entity_id="openai_api_key",
        request=request,
    )
    db.commit()
    return MessageResponse(message="OpenAI API key removed")

