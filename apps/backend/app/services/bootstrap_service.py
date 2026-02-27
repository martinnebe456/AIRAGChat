from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import (
    EmbeddingProfile,
    EvaluationDataset,
    EvaluationDatasetItem,
    ProviderSetting,
    SystemSetting,
    User,
)
from app.db.models.enums import RoleEnum


def bootstrap_defaults(db: Session) -> None:
    settings = get_settings()

    provider_row = db.scalar(select(ProviderSetting).limit(1))
    if provider_row is None:
        provider_row = ProviderSetting(
            active_provider="openai_api",
            model_mappings_json={
                "openai_api": {
                    "default": "gpt-4o-mini",
                },
            },
            openai_config_meta_json={"has_key": False},
            validation_status_json={"openai_api": {"ok": False, "detail": "Awaiting API key validation"}},
        )
        db.add(provider_row)

    defaults = [
        ("rag", "defaults", {
            "chunk_size": settings.rag_chunk_size,
            "chunk_overlap": settings.rag_chunk_overlap,
            "top_k": settings.rag_top_k,
            "min_score": settings.rag_min_score,
            "answer_behavior_mode": settings.rag_answer_behavior_mode,
        }),
        ("prompts", "chat", {
            "template_version": 1,
            "strict_rag_system_prompt": "You are a RAG assistant. Use retrieved context and cite sources.",
            "hybrid_system_prompt": "Prefer retrieved context. If general knowledge is used, say so.",
        }),
        ("eval_defaults", "defaults", {
            "default_dataset_name": "Sample Starter Dataset",
            "metrics_profile": "default",
            "comparison_template": "openai_only",
        }),
        ("telemetry", "frontend", {
            "enabled": True,
            "sampling_rate": 1.0,
            "log_level": settings.log_level,
        }),
        ("models", "defaults", {
            "chat_model_id": "gpt-4o-mini",
            "embedding_model_id": "text-embedding-3-small",
            "embedding_batch_size": 32,
            "eval_judge_model_id": "gpt-4o-mini",
            "pdf_limits": {"max_upload_mb": settings.max_upload_size_mb, "max_pdf_pages": 1000},
        }),
        ("embeddings", "defaults", {
            "provider": "openai_api",
            "model_id": "text-embedding-3-small",
            "batch_size": 32,
            "distance_metric": "cosine",
            "normalize_embeddings": True,
            "input_prefix_mode": "openai_native",
            "qdrant_alias_name": "documents_chunks_active",
        }),
        ("features", "toggles", {
            "chat_history_enabled": True,
            "streaming_enabled": False,
            "ocr_enabled": False,
        }),
        ("maintenance", "queued_ingestion_scheduler", {
            "timezone": "Europe/Prague",
            "last_midnight_run_local_date": None,
            "last_midnight_dispatch_at": None,
            "last_midnight_dispatched_count": 0,
            "last_startup_catchup_at": None,
            "last_startup_catchup_dispatched_count": 0,
            "last_batch_dispatch_id": None,
        }),
    ]
    for namespace, key, value in defaults:
        existing = db.scalar(
            select(SystemSetting).where(SystemSetting.namespace == namespace, SystemSetting.key == key).limit(1)
        )
        if existing is None:
            db.add(SystemSetting(namespace=namespace, key=key, value_json=value, version=1, is_active=True))

    active_embedding_profile = db.scalar(select(EmbeddingProfile).where(EmbeddingProfile.is_active.is_(True)).limit(1))
    if active_embedding_profile is None:
        db.add(
            EmbeddingProfile(
                name="openai-text-embedding-3-small-v1",
                provider="openai_api",
                model_id="text-embedding-3-small",
                dimensions=1536,
                distance_metric="cosine",
                normalize_embeddings=True,
                input_prefix_mode="openai_native",
                qdrant_collection_name=settings.qdrant_collection,
                qdrant_alias_name="documents_chunks_active",
                status="active",
                is_active=True,
                validation_status_json={"status": "bootstrap", "provider": "openai_api"},
            )
        )

    sample_ds = db.scalar(
        select(EvaluationDataset).where(EvaluationDataset.name == "Sample Starter Dataset").limit(1)
    )
    if sample_ds is None:
        ds = EvaluationDataset(
            name="Sample Starter Dataset",
            description="Small seed dataset for local eval smoke testing",
            source_format="json",
            item_count=2,
            status="active",
        )
        db.add(ds)
        db.flush()
        db.add_all(
            [
                EvaluationDatasetItem(
                    dataset_id=ds.id,
                    case_key="sample-1",
                    question="What is this application for?",
                    expected_answer="RAG chat",
                    expected_sources_json=[],
                    expects_refusal=False,
                    metadata_json={"seed": True},
                    tags_json=["seed"],
                ),
                EvaluationDatasetItem(
                    dataset_id=ds.id,
                    case_key="sample-2",
                    question="If there is no context, should the assistant say so?",
                    expected_answer="yes",
                    expected_sources_json=[],
                    expects_refusal=True,
                    metadata_json={"seed": True},
                    tags_json=["seed"],
                ),
            ]
        )


def bootstrap_admin_user(db: Session) -> User:
    settings = get_settings()
    existing = db.scalar(select(User).where(User.username == settings.bootstrap_admin_username).limit(1))
    if existing:
        return existing

    user = User(
        username=settings.bootstrap_admin_username,
        email=settings.bootstrap_admin_email,
        display_name=settings.bootstrap_admin_display_name,
        role=RoleEnum.ADMIN,
        password_hash=hash_password(settings.bootstrap_admin_password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user
