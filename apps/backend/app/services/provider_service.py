from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.providers.inference.openai_provider import OpenAIInferenceProvider
from app.services.secrets_service import SecretsService
from app.services.settings_service import SettingsService


class ProviderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.settings_service = SettingsService(db)
        self.secrets_service = SecretsService(db)

    def get_provider_status(self) -> dict[str, Any]:
        row = self.settings_service.get_provider_settings()
        key_status = self.secrets_service.get_secret_status("openai_api_key")
        models = self.get_models_settings()
        return {
            "active_provider": "openai_api",
            "model_mappings": {"openai_api": {"default": models["chat_model_id"]}},
            "local_validation": {},
            "chat_model_id": models["chat_model_id"],
            "openai_key_status": {
                **key_status,
                **row.openai_config_meta_json,
            },
        }

    def validate_local_runtime(self) -> dict[str, Any]:
        return {"ok": False, "disabled": True, "detail": "Local runtime removed (OpenAI-only mode)"}

    def update_model_mappings(self, *, mappings: dict[str, dict[str, str]], actor_user_id: str | None) -> dict:
        # Deprecated in OpenAI-only mode; keep endpoint compatible but no-op.
        return {"openai_api": {"default": self.resolve_chat_model()}}

    def switch_provider(self, *, provider: str, actor_user_id: str | None) -> dict:
        key_status = self.secrets_service.get_secret_status("openai_api_key")
        if not key_status.get("has_key"):
            raise HTTPException(status_code=400, detail="OpenAI API key is not configured")
        row = self.settings_service.get_provider_settings()
        row.active_provider = "openai_api"
        row.version += 1
        row.updated_by_user_id = actor_user_id
        self.db.flush()
        return {"active_provider": "openai_api"}

    def get_models_settings(self) -> dict[str, Any]:
        try:
            value = self.settings_service.get_namespace("models", "defaults").value_json or {}
        except Exception:  # noqa: BLE001
            value = {}
        return {
            "chat_model_id": str(value.get("chat_model_id") or "gpt-4o-mini"),
            "embedding_model_id": str(value.get("embedding_model_id") or "text-embedding-3-small"),
            "embedding_batch_size": int(value.get("embedding_batch_size") or self.settings.embedding_batch_size),
            "eval_judge_model_id": str(value.get("eval_judge_model_id") or value.get("chat_model_id") or "gpt-4o-mini"),
            "pdf_limits": value.get("pdf_limits") or {"max_upload_mb": self.settings.max_upload_size_mb, "max_pdf_pages": 1000},
        }

    def resolve_chat_model(self) -> str:
        return str(self.get_models_settings()["chat_model_id"])

    def resolve_model_for_category(self, provider: str, category: str) -> str:
        return self.resolve_chat_model()

    def get_inference_provider(self, provider: str | None = None):
        _ = provider  # OpenAI-only
        api_key = self.secrets_service.get_secret("openai_api_key")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key is not configured")
        return OpenAIInferenceProvider(api_key)

    def openai_key_status(self) -> dict[str, Any]:
        row = self.settings_service.get_provider_settings()
        key_status = self.secrets_service.get_secret_status("openai_api_key")
        return {
            "has_key": key_status["has_key"],
            "masked_preview": key_status.get("masked_preview"),
            "last_rotated_at": key_status.get("last_rotated_at"),
            "last_tested_at": (row.openai_config_meta_json or {}).get("last_tested_at"),
            "validation_status": (row.openai_config_meta_json or {}).get("validation_status", {}),
        }

    def set_openai_key(self, *, api_key: str, actor_user_id: str | None) -> dict[str, Any]:
        self.secrets_service.set_secret(name="openai_api_key", value=api_key, actor_user_id=actor_user_id)
        row = self.settings_service.get_provider_settings()
        meta = dict(row.openai_config_meta_json or {})
        meta["has_key"] = True
        meta["validation_status"] = {"status": "unknown"}
        row.openai_config_meta_json = meta
        row.version += 1
        row.updated_by_user_id = actor_user_id
        self.db.flush()
        return self.openai_key_status()

    def test_openai_key(self, *, candidate_key: str | None = None) -> dict[str, Any]:
        key = candidate_key or self.secrets_service.get_secret("openai_api_key")
        if not key:
            raise HTTPException(status_code=400, detail="No OpenAI key available to test")
        provider = OpenAIInferenceProvider(key)
        try:
            models = provider.list_available_models()
            ok = len(models) > 0
            detail = {"ok": ok, "models_count": len(models)}
        except Exception as exc:  # noqa: BLE001
            detail = {"ok": False, "error": str(exc)}
        row = self.settings_service.get_provider_settings()
        meta = dict(row.openai_config_meta_json or {})
        meta["has_key"] = bool(self.secrets_service.get_secret_status("openai_api_key").get("has_key"))
        meta["last_tested_at"] = datetime.now(UTC).isoformat()
        meta["validation_status"] = detail
        row.openai_config_meta_json = meta
        self.db.flush()
        return detail

    def remove_openai_key(self, *, actor_user_id: str | None) -> dict[str, Any]:
        removed = self.secrets_service.remove_secret(name="openai_api_key")
        row = self.settings_service.get_provider_settings()
        meta = dict(row.openai_config_meta_json or {})
        meta["has_key"] = False
        row.openai_config_meta_json = meta
        row.version += 1
        row.updated_by_user_id = actor_user_id
        row.active_provider = "openai_api"
        self.db.flush()
        return {"removed": removed, **self.openai_key_status()}

    def rotate_openai_key(self, *, api_key: str, actor_user_id: str | None) -> dict[str, Any]:
        return self.set_openai_key(api_key=api_key, actor_user_id=actor_user_id)
