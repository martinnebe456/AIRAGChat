from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import DocumentProcessingJob, SystemSetting
from app.services.queued_ingestion_dispatch_service import QueuedIngestionDispatchService


PRAGUE_TZ = ZoneInfo("Europe/Prague")
SCHEDULER_NAMESPACE = "maintenance"
SCHEDULER_KEY = "queued_ingestion_scheduler"
REDIS_LOCK_KEY = "scheduler:queued_ingestion_midnight_dispatch"


class IngestionSchedulerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        settings = get_settings()
        self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self.dispatch_service = QueuedIngestionDispatchService(db)

    @contextmanager
    def _scheduler_lock(self, *, timeout_seconds: int = 60):
        lock = self._redis.lock(REDIS_LOCK_KEY, timeout=timeout_seconds, blocking_timeout=0)
        acquired = False
        try:
            acquired = bool(lock.acquire(blocking=False))
            if not acquired:
                yield False
                return
            yield True
        finally:
            if acquired:
                try:
                    lock.release()
                except Exception:  # noqa: BLE001
                    pass

    def _default_state(self) -> dict[str, Any]:
        return {
            "timezone": "Europe/Prague",
            "last_midnight_run_local_date": None,
            "last_midnight_dispatch_at": None,
            "last_midnight_dispatched_count": 0,
            "last_startup_catchup_at": None,
            "last_startup_catchup_dispatched_count": 0,
            "last_batch_dispatch_id": None,
        }

    def _get_state_row(self) -> SystemSetting:
        row = self.db.scalar(
            select(SystemSetting).where(SystemSetting.namespace == SCHEDULER_NAMESPACE, SystemSetting.key == SCHEDULER_KEY).limit(1)
        )
        if row is None:
            row = SystemSetting(
                namespace=SCHEDULER_NAMESPACE,
                key=SCHEDULER_KEY,
                version=1,
                is_active=True,
                value_json=self._default_state(),
            )
            self.db.add(row)
            self.db.flush()
        return row

    def _get_state(self) -> dict[str, Any]:
        row = self._get_state_row()
        value = row.value_json if isinstance(row.value_json, dict) else {}
        state = self._default_state()
        state.update(value)
        return state

    def _save_state(self, state: dict[str, Any]) -> None:
        row = self._get_state_row()
        merged = self._default_state()
        merged.update(state)
        row.value_json = merged
        row.version = int(row.version or 1) + 1
        self.db.flush()

    @staticmethod
    def _now_utc(now_utc: datetime | None = None) -> datetime:
        now = now_utc or datetime.now(UTC)
        if now.tzinfo is None:
            return now.replace(tzinfo=UTC)
        return now.astimezone(UTC)

    def _today_prague(self, now_utc: datetime | None = None) -> str:
        return self._now_utc(now_utc).astimezone(PRAGUE_TZ).date().isoformat()

    def next_midnight_prague(self, now_utc: datetime | None = None) -> datetime:
        now = self._now_utc(now_utc).astimezone(PRAGUE_TZ)
        next_day = now.date() + timedelta(days=1)
        midnight_local = datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0, tzinfo=PRAGUE_TZ)
        return midnight_local.astimezone(UTC)

    def _queued_count_global(self) -> int:
        return int(
            self.db.scalar(
                select(func.count(DocumentProcessingJob.id)).where(DocumentProcessingJob.status == "queued")
            )
            or 0
        )

    def get_scheduler_status(self, now_utc: datetime | None = None) -> dict[str, Any]:
        state = self._get_state()
        today_local = self._today_prague(now_utc)
        missed = bool(
            self._queued_count_global() > 0
            and state.get("last_midnight_run_local_date") != today_local
        )
        return {
            "timezone": "Europe/Prague",
            "last_midnight_run_local_date": state.get("last_midnight_run_local_date"),
            "last_midnight_dispatch_at": state.get("last_midnight_dispatch_at"),
            "last_midnight_dispatched_count": int(state.get("last_midnight_dispatched_count") or 0),
            "missed_run_detected": missed,
            "last_startup_catchup_at": state.get("last_startup_catchup_at"),
            "last_startup_catchup_dispatched_count": int(state.get("last_startup_catchup_dispatched_count") or 0),
            "next_midnight_at_utc": self.next_midnight_prague(now_utc),
        }

    def run_midnight_dispatch_if_due(self, now_utc: datetime | None = None) -> dict[str, Any]:
        now = self._now_utc(now_utc)
        local_date = self._today_prague(now)
        with self._scheduler_lock() as acquired:
            if not acquired:
                return {"ok": False, "reason": "lock_not_acquired", "dispatched_count": 0}
            state = self._get_state()
            if state.get("last_midnight_run_local_date") == local_date:
                return {"ok": True, "skipped": True, "reason": "already_ran", "dispatched_count": 0}

            result = self.dispatch_service.dispatch_queued_global(trigger="midnight_scheduler")
            state.update(
                {
                    "timezone": "Europe/Prague",
                    "last_midnight_run_local_date": local_date,
                    "last_midnight_dispatch_at": now.isoformat(),
                    "last_midnight_dispatched_count": int(result.get("dispatched_count") or 0),
                    "last_batch_dispatch_id": result.get("batch_dispatch_id"),
                }
            )
            self._save_state(state)
            self.db.commit()
            return {"ok": True, "skipped": False, **result}

    def run_startup_catchup_if_missed(self, now_utc: datetime | None = None) -> dict[str, Any]:
        now = self._now_utc(now_utc)
        local_date = self._today_prague(now)
        with self._scheduler_lock() as acquired:
            if not acquired:
                return {"ok": False, "reason": "lock_not_acquired", "dispatched_count": 0}
            state = self._get_state()
            queued_count = self._queued_count_global()
            if queued_count <= 0:
                return {"ok": True, "skipped": True, "reason": "no_queued_jobs", "dispatched_count": 0}
            if state.get("last_midnight_run_local_date") == local_date:
                return {"ok": True, "skipped": True, "reason": "midnight_already_ran", "dispatched_count": 0}

            result = self.dispatch_service.dispatch_queued_global(trigger="startup_catchup")
            state.update(
                {
                    "timezone": "Europe/Prague",
                    "last_startup_catchup_at": now.isoformat(),
                    "last_startup_catchup_dispatched_count": int(result.get("dispatched_count") or 0),
                    "last_batch_dispatch_id": result.get("batch_dispatch_id"),
                }
            )
            self._save_state(state)
            self.db.commit()
            return {"ok": True, "skipped": False, **result}
