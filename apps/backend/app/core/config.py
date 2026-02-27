from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="AIRAGChat", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    jwt_secret: str = Field(default="change-me-local-jwt-secret", alias="APP_JWT_SECRET")
    access_token_expire_minutes: int = Field(default=15, alias="APP_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="APP_REFRESH_TOKEN_EXPIRE_DAYS")
    cookie_secure: bool = Field(default=False, alias="APP_COOKIE_SECURE")

    cors_origins_raw: str = Field(default="http://localhost:5173", alias="APP_CORS_ORIGINS")
    rate_limit_login_per_min: int = Field(default=5, alias="APP_RATE_LIMIT_LOGIN_PER_MIN")
    rate_limit_chat_per_min: int = Field(default=30, alias="APP_RATE_LIMIT_CHAT_PER_MIN")

    database_url: str = Field(
        default="postgresql+psycopg://airagchat:airagchat@postgres:5432/airagchat",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/1", alias="CELERY_RESULT_BACKEND")

    qdrant_host: str = Field(default="qdrant", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_collection: str = Field(default="documents_chunks", alias="QDRANT_COLLECTION")

    uploads_dir: str = Field(default="/app/data/uploads", alias="UPLOADS_DIR")
    max_upload_size_mb: int = Field(default=25, alias="MAX_UPLOAD_SIZE_MB")
    max_pdf_pages: int = Field(default=1000, alias="MAX_PDF_PAGES")
    pdf_ocr_enabled: bool = Field(default=False, alias="PDF_OCR_ENABLED")

    embedding_model_id: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL_ID")
    embedding_batch_size: int = Field(default=16, alias="EMBEDDING_BATCH_SIZE")
    openai_chat_model: str = Field(default="gpt-4o-mini", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")

    rag_chunk_size: int = Field(default=900, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=150, alias="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    rag_min_score: float = Field(default=0.15, alias="RAG_MIN_SCORE")
    rag_answer_behavior_mode: Literal["strict_rag_only", "hybrid_with_disclaimer"] = Field(
        default="strict_rag_only",
        alias="RAG_ANSWER_BEHAVIOR_MODE",
    )

    provider_active: str = Field(
        default="openai_api",
        alias="PROVIDER_ACTIVE",
    )
    openai_enabled: bool = Field(default=False, alias="OPENAI_ENABLED")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    secrets_master_key: str = Field(default="", alias="APP_SECRETS_MASTER_KEY")

    bootstrap_admin_username: str = Field(default="admin", alias="APP_BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_email: str = Field(default="admin@example.local", alias="APP_BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_password: str = Field(default="ChangeMe123!", alias="APP_BOOTSTRAP_ADMIN_PASSWORD")
    bootstrap_admin_display_name: str = Field(default="Administrator", alias="APP_BOOTSTRAP_ADMIN_DISPLAY_NAME")

    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://otel-collector:4317",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_service_name: str = Field(default="airagchat-backend", alias="OTEL_SERVICE_NAME")
    otel_sampler: str = Field(default="parentbased_traceidratio", alias="OTEL_TRACES_SAMPLER")
    otel_sampler_arg: float = Field(default=1.0, alias="OTEL_TRACES_SAMPLER_ARG")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def uploads_path(self) -> Path:
        p = Path(self.uploads_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_env != "test" and not settings.secrets_master_key:
        raise ValueError("APP_SECRETS_MASTER_KEY must be set")
    return settings
