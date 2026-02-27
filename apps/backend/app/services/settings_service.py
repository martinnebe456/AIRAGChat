from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models import ProviderSetting, SystemSetting


class SettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_namespace(self, namespace: str, key: str) -> SystemSetting:
        row = self.db.scalar(
            select(SystemSetting).where(SystemSetting.namespace == namespace, SystemSetting.key == key).limit(1)
        )
        if row is None:
            raise HTTPException(status_code=404, detail=f"Setting not found: {namespace}/{key}")
        return row

    def update_namespace(self, namespace: str, key: str, value_json, updated_by_user_id: str | None):  # noqa: ANN001
        row = self.get_namespace(namespace, key)
        row.value_json = value_json
        row.version += 1
        row.updated_by_user_id = updated_by_user_id
        self.db.flush()
        return row

    def get_provider_settings(self) -> ProviderSetting:
        row = self.db.scalar(select(ProviderSetting).limit(1))
        if row is None:
            raise ValueError("Provider settings missing")
        return row
