from __future__ import annotations

from cryptography.fernet import Fernet

from app.core.config import get_settings


class SecretsCipher:
    def __init__(self) -> None:
        settings = get_settings()
        self._fernet = Fernet(settings.secrets_master_key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

