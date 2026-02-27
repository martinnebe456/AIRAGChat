from __future__ import annotations

from contextlib import contextmanager

import redis

from app.core.config import get_settings


class DocumentLockUnavailableError(RuntimeError):
    pass


class DocumentLockService:
    def __init__(self) -> None:
        settings = get_settings()
        self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    @contextmanager
    def lock(
        self,
        document_id: str,
        *,
        timeout_seconds: int = 120,
        blocking_timeout_seconds: int = 2,
    ):
        lock = self._redis.lock(
            f"doc_lock:{document_id}",
            timeout=timeout_seconds,
            blocking_timeout=blocking_timeout_seconds,
        )
        acquired = False
        try:
            acquired = bool(lock.acquire(blocking=True))
            if not acquired:
                raise DocumentLockUnavailableError(f"Document is busy: {document_id}")
            yield
        finally:
            if acquired:
                try:
                    lock.release()
                except Exception:  # noqa: BLE001
                    pass

