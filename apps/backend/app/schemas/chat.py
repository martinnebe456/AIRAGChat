from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    project_id: str | None = None
    document_ids: list[str] | None = None


class Citation(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    snippet: str
    score: float | None = None
    page: int | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ChatAskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    provider: str
    resolved_model_id: str
    answer_mode: str
    latency_ms: int
    usage: TokenUsage | None = None
    session_id: str
    message_id: str
    project_id: str | None = None


class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    project_id: str | None = None
    title: str
    is_archived: bool
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]
    total: int


class CreateChatSessionRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=255)
    project_id: str


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    user_id: str | None = None
    role: str
    content: str
    message_index: int
    provider: str | None = None
    provider_model_id: str | None = None
    model_category: str | None = None  # legacy field, no longer set in OpenAI-only chat flow
    answer_mode: str | None = None
    citations_json: Any | None = None
    retrieval_metadata_json: Any | None = None
    token_usage_json: Any | None = None
    latency_ms: int | None = None
    status: str
    project_id_snapshot: str | None = None
    project_name_snapshot: str | None = None
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]
    total: int
