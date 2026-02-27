from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class SystemSetting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "system_settings"

    namespace: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    value_json: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    updated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class ProviderSetting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "provider_settings"

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="openai_api")
    model_mappings_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    openai_config_meta_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    validation_status_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class SecretStore(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "secrets_store"

    secret_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    masked_preview: Mapped[str] = mapped_column(String(255), nullable=False)
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    updated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class AuditLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    before_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
