from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvalDatasetResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: str
    version: int
    source_format: str
    item_count: int
    created_at: datetime
    updated_at: datetime


class EvalDatasetListResponse(BaseModel):
    items: list[EvalDatasetResponse]
    total: int


class EvalDatasetImportRequest(BaseModel):
    name: str
    description: str | None = None
    source_format: str = Field(pattern="^(json|jsonl|csv)$")
    items: list[dict[str, Any]]


class EvalRunCreateRequest(BaseModel):
    dataset_id: str
    provider: str = Field(default="openai_api", pattern="^(openai_api)$")
    model_category: str = Field(default="medium", pattern="^(low|medium|high)$")
    rag_overrides: dict[str, Any] | None = None


class EvalRunResponse(BaseModel):
    id: str
    dataset_id: str | None = None
    status: str
    provider: str
    model_category: str
    resolved_model_id: str | None = None
    config_snapshot_json: dict[str, Any]
    error_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class EvalRunListResponse(BaseModel):
    items: list[EvalRunResponse]
    total: int


class EvalRunItemResponse(BaseModel):
    id: str
    run_id: str
    status: str
    question: str
    answer_text: str | None = None
    metrics_json: dict[str, Any] | list[Any] | None = None
    latency_ms: int | None = None
    created_at: datetime


class EvalRunItemListResponse(BaseModel):
    items: list[EvalRunItemResponse]
    total: int


class EvalCompareResponse(BaseModel):
    run_a: EvalRunResponse
    run_b: EvalRunResponse
    deltas: dict[str, Any]
