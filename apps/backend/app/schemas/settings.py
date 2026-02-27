from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SettingsNamespaceResponse(BaseModel):
    namespace: str
    key: str
    value_json: dict[str, Any] | list[Any]
    version: int
    updated_at: datetime


class SettingsNamespaceUpdateRequest(BaseModel):
    value_json: dict[str, Any] | list[Any]


class PublicClientSettingsResponse(BaseModel):
    frontend_telemetry_enabled: bool
    frontend_telemetry_sampling_rate: float
    log_level: str


class ModelSettingsResponse(BaseModel):
    namespace: str
    key: str
    value_json: dict[str, Any]
    version: int
    updated_at: datetime


class ModelSettingsUpdateRequest(BaseModel):
    chat_model_id: str = Field(min_length=1, max_length=255)
    embedding_model_id: str = Field(min_length=1, max_length=255)
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    eval_judge_model_id: str | None = Field(default=None, max_length=255)
    pdf_limits: dict[str, int] = Field(default_factory=lambda: {"max_upload_mb": 100, "max_pdf_pages": 1000})


class ProviderStatusResponse(BaseModel):
    active_provider: str
    model_mappings: dict[str, dict[str, str]]
    local_validation: dict[str, Any] = Field(default_factory=dict)
    openai_key_status: dict[str, Any] = Field(default_factory=dict)


class ProviderSwitchRequest(BaseModel):
    provider: str = Field(pattern="^(openai_api)$")


class ProviderModelMappingsUpdateRequest(BaseModel):
    model_mappings: dict[str, dict[str, str]]


class OpenAIKeySetRequest(BaseModel):
    api_key: str = Field(min_length=10, max_length=512)


class OpenAIKeyTestRequest(BaseModel):
    api_key: str | None = Field(default=None, min_length=10, max_length=512)


class OpenAIKeyStatusResponse(BaseModel):
    has_key: bool
    masked_preview: str | None = None
    last_rotated_at: datetime | None = None
    last_tested_at: datetime | None = None
    validation_status: dict[str, Any] = Field(default_factory=dict)


class EmbeddingProfileSummary(BaseModel):
    id: str
    name: str
    provider: str
    model_id: str
    dimensions: int
    distance_metric: str
    normalize_embeddings: bool
    input_prefix_mode: str
    qdrant_collection_name: str
    qdrant_alias_name: str | None = None
    status: str
    is_active: bool
    validation_status_json: dict[str, Any] | list[Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class EmbeddingSettingsResponse(BaseModel):
    namespace: str
    key: str
    value_json: dict[str, Any]
    version: int
    updated_at: datetime
    active_profile: EmbeddingProfileSummary | None = None
    latest_draft_profile: EmbeddingProfileSummary | None = None


class EmbeddingSettingsUpdateRequest(BaseModel):
    provider: str = Field(pattern="^(openai_api)$")
    model_id: str = Field(min_length=1, max_length=255)
    batch_size: int = Field(default=16, ge=1, le=256)
    distance_metric: str = Field(default="cosine", pattern="^(cosine)$")
    normalize_embeddings: bool = True
    input_prefix_mode: str = Field(default="e5", pattern="^(e5|none|openai_native)$")
    qdrant_alias_name: str = Field(default="documents_chunks_active", min_length=1, max_length=255)
    create_draft_profile: bool = True


class EmbeddingProviderValidateRequest(BaseModel):
    provider: str = Field(pattern="^(openai_api)$")
    model_id: str = Field(min_length=1, max_length=255)
    batch_size: int = Field(default=16, ge=1, le=256)
    input_prefix_mode: str = Field(default="e5", pattern="^(e5|none|openai_native)$")


class EmbeddingProviderValidateResponse(BaseModel):
    ok: bool
    provider: str
    model_id: str
    dimensions: int | None = None
    detail: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddingStatusResponse(BaseModel):
    active_alias_name: str
    active_alias_target: str | None = None
    active_profile: EmbeddingProfileSummary | None = None
    latest_draft_profile: EmbeddingProfileSummary | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    openai_key_status: dict[str, Any] = Field(default_factory=dict)
    reindex_summary: dict[str, Any] = Field(default_factory=dict)


class EmbeddingReindexRunCreateRequest(BaseModel):
    target_embedding_profile_id: str | None = None
    use_latest_draft: bool = True
    scope: dict[str, Any] = Field(default_factory=lambda: {"kind": "all_documents"})


class EmbeddingReindexRunResponse(BaseModel):
    id: str
    target_embedding_profile_id: str
    source_embedding_profile_id: str | None = None
    status: str
    scope_json: dict[str, Any] | list[Any]
    qdrant_staging_collection: str
    started_by_user_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    applied_by_user_id: str | None = None
    applied_at: datetime | None = None
    summary_json: dict[str, Any] | list[Any] = Field(default_factory=dict)
    drift_detected_count: int = 0
    error_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class EmbeddingReindexRunListResponse(BaseModel):
    items: list[EmbeddingReindexRunResponse]
    total: int


class EmbeddingReindexRunItemResponse(BaseModel):
    id: str
    run_id: str
    document_id: str
    status: str
    attempt_count: int
    document_content_hash_snapshot: str | None = None
    indexed_chunk_count: int
    error_summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_seen_document_updated_at: datetime | None = None
    needs_catchup: bool
    created_at: datetime
    updated_at: datetime


class EmbeddingReindexRunItemListResponse(BaseModel):
    items: list[EmbeddingReindexRunItemResponse]
    total: int


class EmbeddingReindexApplyResponse(BaseModel):
    run_id: str
    applied: bool
    status: str
    active_alias_name: str
    active_alias_target: str | None = None
    catchup_summary: dict[str, Any] = Field(default_factory=dict)
