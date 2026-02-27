from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.rate_limit import enforce_rate_limit
from app.db.models import User
from app.db.session import get_db
from app.schemas.chat import (
    ChatAskRequest,
    ChatAskResponse,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    CreateChatSessionRequest,
)
from app.services.chat_service import ChatService

router = APIRouter()


def _session_response(s) -> ChatSessionResponse:  # noqa: ANN001
    return ChatSessionResponse(
        id=s.id,
        user_id=s.user_id,
        project_id=getattr(s, "project_id", None),
        title=s.title,
        is_archived=s.is_archived,
        last_message_at=s.last_message_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _message_response(m) -> ChatMessageResponse:  # noqa: ANN001
    return ChatMessageResponse(
        id=m.id,
        session_id=m.session_id,
        user_id=m.user_id,
        role=m.role,
        content=m.content,
        message_index=m.message_index,
        provider=m.provider,
        provider_model_id=m.provider_model_id,
        model_category=m.model_category,
        answer_mode=m.answer_mode,
        citations_json=m.citations_json,
        retrieval_metadata_json=m.retrieval_metadata_json,
        token_usage_json=m.token_usage_json,
        latency_ms=m.latency_ms,
        status=m.status,
        project_id_snapshot=getattr(m, "project_id_snapshot", None),
        project_name_snapshot=getattr(m, "project_name_snapshot", None),
        created_at=m.created_at,
    )


@router.post("/ask", response_model=ChatAskResponse)
def ask(
    payload: ChatAskRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatAskResponse:
    enforce_rate_limit("chat", current_user.id)
    result = ChatService(db).ask(
        current_user=current_user,
        question=payload.question,
        session_id=payload.session_id,
        project_id=payload.project_id,
        document_ids=payload.document_ids,
    )
    db.commit()
    return ChatAskResponse(**result)


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionListResponse:
    items, total = ChatService(db).list_sessions(user_id=current_user.id, include_archived=include_archived)
    return ChatSessionListResponse(items=[_session_response(i) for i in items], total=total)


@router.post("/sessions", response_model=ChatSessionResponse)
def create_session(
    payload: CreateChatSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionResponse:
    session = ChatService(db).create_session(user=current_user, title=payload.title, project_id=payload.project_id)
    db.commit()
    return _session_response(session)


@router.get("/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
def list_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageListResponse:
    items, total = ChatService(db).list_messages(session_id=session_id, user_id=current_user.id)
    return ChatMessageListResponse(items=[_message_response(i) for i in items], total=total)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    ChatService(db).delete_session(session_id=session_id, user_id=current_user.id)
    db.commit()
    return {"message": "Chat session archived"}
