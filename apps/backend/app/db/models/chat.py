from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class ChatSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_index: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_model_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    answer_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    citations_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    retrieval_metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    token_usage_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    project_id_snapshot: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    project_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
