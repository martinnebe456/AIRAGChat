from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(slots=True)
class ProviderHealth:
    ok: bool
    detail: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderModelInfo:
    id: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    warnings: list[str] = field(default_factory=list)
    detail: str | None = None


@dataclass(slots=True)
class InferenceRequest:
    model_id: str
    prompt: str
    system_prompt: str | None = None
    conversation: list[dict[str, str]] = field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InferenceResult:
    text: str
    model_id: str
    provider: str
    latency_ms: int
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EmbeddingBatchResult:
    vectors: list[list[float]]
    model_id: str
    dimension: int


@dataclass(slots=True)
class EvalBatchRequest:
    items: list[dict[str, Any]]
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvalBatchResult:
    items: list[dict[str, Any]]
    summary: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class InferenceProvider(Protocol):
    def generate(self, request: InferenceRequest) -> InferenceResult: ...
    def list_available_models(self) -> list[ProviderModelInfo]: ...
    def validate_model(self, model_id: str) -> ValidationResult: ...


class EmbeddingProvider(Protocol):
    def embed_texts(
        self,
        texts: list[str],
        input_kind: Literal["document", "query"],
    ) -> EmbeddingBatchResult: ...
    def dimension(self) -> int: ...
    def health(self) -> ProviderHealth: ...


class EvaluationProvider(Protocol):
    def run_evaluation_batch(self, request: EvalBatchRequest) -> EvalBatchResult: ...
    def capabilities(self) -> dict[str, Any]: ...
    def health(self) -> ProviderHealth: ...

