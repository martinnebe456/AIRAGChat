from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, status

from app.core.config import get_settings


class _RateMemoryStore:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        hits = self._hits[key]
        hits[:] = [ts for ts in hits if ts > cutoff]
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


_store = _RateMemoryStore()


def enforce_rate_limit(kind: str, identifier: str) -> None:
    settings = get_settings()
    limit = settings.rate_limit_login_per_min if kind == "login" else settings.rate_limit_chat_per_min
    if not _store.check(f"{kind}:{identifier}", limit, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {kind}",
        )

