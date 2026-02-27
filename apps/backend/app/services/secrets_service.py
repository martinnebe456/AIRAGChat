from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import SecretsCipher
from app.core.security import mask_secret
from app.db.models import SecretStore


class SecretsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.cipher = SecretsCipher()

    def set_secret(self, *, name: str, value: str, actor_user_id: str | None = None) -> SecretStore:
        row = self.db.scalar(select(SecretStore).where(SecretStore.secret_name == name).limit(1))
        masked = mask_secret(value)
        if row is None:
            row = SecretStore(
                secret_name=name,
                ciphertext=self.cipher.encrypt(value),
                masked_preview=masked,
                last_rotated_at=datetime.now(UTC),
                metadata_json={},
                updated_by_user_id=actor_user_id,
            )
            self.db.add(row)
        else:
            row.ciphertext = self.cipher.encrypt(value)
            row.masked_preview = masked
            row.last_rotated_at = datetime.now(UTC)
            row.updated_by_user_id = actor_user_id
        self.db.flush()
        return row

    def get_secret(self, name: str) -> str | None:
        row = self.db.scalar(select(SecretStore).where(SecretStore.secret_name == name).limit(1))
        if row is None:
            return None
        return self.cipher.decrypt(row.ciphertext)

    def get_secret_status(self, name: str) -> dict:
        row = self.db.scalar(select(SecretStore).where(SecretStore.secret_name == name).limit(1))
        if row is None:
            return {"has_key": False, "masked_preview": None, "last_rotated_at": None}
        return {
            "has_key": True,
            "masked_preview": row.masked_preview,
            "last_rotated_at": row.last_rotated_at,
        }

    def remove_secret(self, *, name: str) -> bool:
        row = self.db.scalar(select(SecretStore).where(SecretStore.secret_name == name).limit(1))
        if row is None:
            return False
        self.db.delete(row)
        self.db.flush()
        return True

