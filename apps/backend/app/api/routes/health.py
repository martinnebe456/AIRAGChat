from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal

router = APIRouter()


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict[str, str]:
    settings = get_settings()
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}


@router.get("/health/deps")
def deps() -> dict:
    settings = get_settings()
    return {
        "postgres": {"configured": True},
        "redis": {"url": settings.redis_url},
        "qdrant": {"host": settings.qdrant_host, "port": settings.qdrant_port},
        "openai": {"base_url": settings.openai_base_url, "chat_model": settings.openai_chat_model, "embedding_model": settings.openai_embedding_model},
    }
