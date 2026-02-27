from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.models import User
from app.db.models.enums import RoleEnum
from app.db.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.settings import OpenAIKeySetRequest, OpenAIKeyStatusResponse, OpenAIKeyTestRequest
from app.services.audit_service import AuditService
from app.services.provider_service import ProviderService

router = APIRouter()


@router.get("/status", response_model=OpenAIKeyStatusResponse)
def openai_status(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> OpenAIKeyStatusResponse:
    return OpenAIKeyStatusResponse(**ProviderService(db).openai_key_status())


@router.put("/key", response_model=OpenAIKeyStatusResponse)
def set_openai_key(
    payload: OpenAIKeySetRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> OpenAIKeyStatusResponse:
    status_data = ProviderService(db).set_openai_key(api_key=payload.api_key, actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="openai.key.set",
        entity_type="secret",
        entity_id="openai_api_key",
        request=request,
    )
    db.commit()
    return OpenAIKeyStatusResponse(**status_data)


@router.post("/key/test")
def test_openai_key(
    payload: OpenAIKeyTestRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> dict:
    result = ProviderService(db).test_openai_key(candidate_key=payload.api_key)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="openai.key.test",
        entity_type="secret",
        entity_id="openai_api_key",
        request=request,
        after_json=result,
    )
    db.commit()
    return result


@router.post("/key/rotate", response_model=OpenAIKeyStatusResponse)
def rotate_openai_key(
    payload: OpenAIKeySetRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> OpenAIKeyStatusResponse:
    status_data = ProviderService(db).rotate_openai_key(api_key=payload.api_key, actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="openai.key.rotate",
        entity_type="secret",
        entity_id="openai_api_key",
        request=request,
    )
    db.commit()
    return OpenAIKeyStatusResponse(**status_data)


@router.delete("/key", response_model=MessageResponse)
def delete_openai_key(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> MessageResponse:
    ProviderService(db).remove_openai_key(actor_user_id=admin.id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="openai.key.delete",
        entity_type="secret",
        entity_id="openai_api_key",
        request=request,
    )
    db.commit()
    return MessageResponse(message="OpenAI API key removed")

