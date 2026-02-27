from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.providers.interfaces import (
    InferenceRequest,
    InferenceResult,
    ProviderModelInfo,
    ValidationResult,
)


class OpenAIInferenceProvider:
    provider_name = "openai_api"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.settings = get_settings()
        self.base_url = self.settings.openai_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, request: InferenceRequest) -> InferenceResult:
        payload: dict[str, Any] = {
            "model": request.model_id,
            "messages": [],
            "temperature": request.temperature,
        }
        if request.system_prompt:
            payload["messages"].append({"role": "system", "content": request.system_prompt})
        payload["messages"].extend(request.conversation)
        payload["messages"].append({"role": "user", "content": request.prompt})
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        start = time.perf_counter()
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{self.base_url}/chat/completions", json=payload, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        text = ""
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            text = str((choices[0].get("message") or {}).get("content", ""))
        return InferenceResult(
            text=text,
            model_id=request.model_id,
            provider=self.provider_name,
            latency_ms=int((time.perf_counter() - start) * 1000),
            usage=data.get("usage") or {},
            raw=data,
        )

    def list_available_models(self) -> list[ProviderModelInfo]:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{self.base_url}/models", headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        return [ProviderModelInfo(id=str(item.get("id"))) for item in items if item.get("id")]

    def validate_model(self, model_id: str) -> ValidationResult:
        try:
            ids = {m.id for m in self.list_available_models()}
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(valid=False, detail=str(exc))
        return ValidationResult(valid=model_id in ids, detail="ok" if model_id in ids else "missing")

