from __future__ import annotations

import time
from typing import Any, Literal

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import get_settings
from app.providers.interfaces import EmbeddingBatchResult, ProviderHealth


class OpenAIEmbeddingProvider:
    provider_name = "openai_api"

    def __init__(
        self,
        api_key: str,
        *,
        model_id: str,
        batch_size: int = 64,
        input_prefix_mode: str = "openai_native",
        cached_dimension: int | None = None,
    ) -> None:
        self.settings = get_settings()
        self.api_key = api_key
        self.model_id = model_id
        self.batch_size = batch_size
        self.input_prefix_mode = input_prefix_mode
        self.base_url = self.settings.openai_base_url.rstrip("/")
        self._dimension = cached_dimension

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _prepare_text(self, text: str, input_kind: Literal["document", "query"]) -> str:
        if self.input_prefix_mode == "e5":
            return f"{'query' if input_kind == 'query' else 'passage'}: {text}"
        return text

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def embed_texts(self, texts: list[str], input_kind: Literal["document", "query"]) -> EmbeddingBatchResult:
        vectors: list[list[float]] = []
        prepared = [self._prepare_text(t, input_kind) for t in texts]
        with httpx.Client(timeout=60) as client:
            for i in range(0, len(prepared), self.batch_size):
                batch = prepared[i : i + self.batch_size]
                payload: dict[str, Any] = {
                    "model": self.model_id,
                    "input": batch,
                    "encoding_format": "float",
                }
                start = time.perf_counter()
                resp = client.post(f"{self.base_url}/embeddings", json=payload, headers=self._headers())
                _ = int((time.perf_counter() - start) * 1000)
                resp.raise_for_status()
                data = resp.json()
                for item in sorted(data.get("data") or [], key=lambda x: x.get("index", 0)):
                    emb = item.get("embedding") or []
                    row = [float(v) for v in emb]
                    if self._dimension is None and row:
                        self._dimension = len(row)
                    vectors.append(row)
        dim = self._dimension or (len(vectors[0]) if vectors else 0)
        return EmbeddingBatchResult(vectors=vectors, model_id=self.model_id, dimension=dim)

    def dimension(self) -> int:
        if self._dimension:
            return self._dimension
        result = self.embed_texts(["dimension probe"], input_kind="query")
        self._dimension = result.dimension
        return self._dimension

    def health(self) -> ProviderHealth:
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(f"{self.base_url}/models", headers=self._headers())
            resp.raise_for_status()
            return ProviderHealth(ok=True, detail="OpenAI models endpoint reachable")
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, detail=str(exc))

