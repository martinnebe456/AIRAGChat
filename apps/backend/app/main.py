from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.errors.handlers import register_exception_handlers
from app.api.routes import chat, documents, health, ingestion, projects, users
from app.api.routes import auth as auth_router
from app.api.routes import admin_embeddings, admin_openai, admin_providers, evals, settings, telemetry
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.telemetry import configure_telemetry
from app.db.session import SessionLocal
from app.services.bootstrap_service import bootstrap_admin_user, bootstrap_defaults
from app.services.ingestion_scheduler_service import IngestionSchedulerService


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    app_settings = get_settings()
    configure_logging(app_settings)
    configure_telemetry(app_settings)
    logger = get_logger(__name__)
    logger.info("startup.begin", extra={"event": "startup"})
    with SessionLocal() as db:
        bootstrap_defaults(db)
        bootstrap_admin_user(db)
        db.commit()
        try:
            catchup_result = IngestionSchedulerService(db).run_startup_catchup_if_missed()
            logger.info("startup.ingestion_queue_catchup", extra={"event": "startup_ingestion_queue_catchup", "result": catchup_result})
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.warning(
                "startup.ingestion_queue_catchup_failed",
                extra={"event": "startup_ingestion_queue_catchup_failed", "error": str(exc)},
            )
    yield
    logger.info("shutdown.complete", extra={"event": "shutdown"})


def create_app() -> FastAPI:
    app_settings = get_settings()
    app = FastAPI(
        title="AIRAGChat API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(auth_router.router, prefix="/api/v1/auth")
    app.include_router(users.router, prefix="/api/v1/users")
    app.include_router(projects.router, prefix="/api/v1/projects")
    app.include_router(documents.router, prefix="/api/v1/documents")
    app.include_router(ingestion.router, prefix="/api/v1/ingestion")
    app.include_router(chat.router, prefix="/api/v1/chat")
    app.include_router(settings.router, prefix="/api/v1/settings")
    app.include_router(admin_providers.router, prefix="/api/v1/admin/providers")
    app.include_router(admin_openai.router, prefix="/api/v1/admin/openai")
    app.include_router(admin_embeddings.router, prefix="/api/v1/admin/embeddings")
    app.include_router(evals.router, prefix="/api/v1/evals")
    app.include_router(telemetry.router, prefix="/api/v1/telemetry")
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
