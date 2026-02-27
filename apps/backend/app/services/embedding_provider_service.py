from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from fastapi import HTTPException
import httpx
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import EmbeddingProfile, EmbeddingReindexRun, EmbeddingReindexRunItem, SystemSetting
from app.providers.embeddings.openai_embedding_provider import OpenAIEmbeddingProvider
from app.providers.interfaces import EmbeddingProvider
from app.services.secrets_service import SecretsService


EMBEDDINGS_NAMESPACE = "embeddings"
EMBEDDINGS_KEY = "defaults"
DEFAULT_ALIAS_NAME = "documents_chunks_active"


def _slugify_model(model_id: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", model_id.strip()).strip("-").lower()
    return slug or "model"


class EmbeddingProviderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.secrets_service = SecretsService(db)
        self.qdrant = QdrantClient(host=self.settings.qdrant_host, port=self.settings.qdrant_port)
        self.qdrant_http_base = f"http://{self.settings.qdrant_host}:{self.settings.qdrant_port}"

    def _default_settings_value(self) -> dict[str, Any]:
        return {
            "provider": "openai_api",
            "model_id": "text-embedding-3-small",
            "batch_size": 32,
            "distance_metric": "cosine",
            "normalize_embeddings": True,
            "input_prefix_mode": "openai_native",
            "qdrant_alias_name": DEFAULT_ALIAS_NAME,
        }

    def _ensure_settings_row(self) -> SystemSetting:
        row = self.db.scalar(
            select(SystemSetting)
            .where(SystemSetting.namespace == EMBEDDINGS_NAMESPACE, SystemSetting.key == EMBEDDINGS_KEY)
            .limit(1)
        )
        if row is None:
            row = SystemSetting(
                namespace=EMBEDDINGS_NAMESPACE,
                key=EMBEDDINGS_KEY,
                value_json=self._default_settings_value(),
                version=1,
                is_active=True,
            )
            self.db.add(row)
            self.db.flush()
        return row

    def _ensure_bootstrap_profile(self) -> EmbeddingProfile:
        active = self.db.scalar(select(EmbeddingProfile).where(EmbeddingProfile.is_active.is_(True)).limit(1))
        if active:
            return active
        profile = EmbeddingProfile(
            name="openai-text-embedding-3-small-v1",
            provider="openai_api",
            model_id="text-embedding-3-small",
            dimensions=1536,
            distance_metric="cosine",
            normalize_embeddings=True,
            input_prefix_mode="openai_native",
            qdrant_collection_name=self.settings.qdrant_collection,
            qdrant_alias_name=DEFAULT_ALIAS_NAME,
            status="active",
            is_active=True,
            validation_status_json={"status": "bootstrap", "provider": "openai_api"},
        )
        self.db.add(profile)
        self.db.flush()
        return profile

    def ensure_bootstrap_state(self) -> None:
        self._ensure_settings_row()
        profile = self._ensure_bootstrap_profile()
        self.ensure_alias_bootstrap(alias_name=profile.qdrant_alias_name or DEFAULT_ALIAS_NAME, fallback_collection=profile.qdrant_collection_name)

    def get_settings_row(self) -> SystemSetting:
        self.ensure_bootstrap_state()
        return self._ensure_settings_row()

    def get_settings_value(self) -> dict[str, Any]:
        row = self.get_settings_row()
        value = dict(self._default_settings_value())
        value.update((row.value_json or {}))
        if str(value.get("provider") or "") != "openai_api":
            # OpenAI-only mode: ignore legacy local embedding settings in reads.
            qdrant_alias_name = value.get("qdrant_alias_name") or DEFAULT_ALIAS_NAME
            value = dict(self._default_settings_value())
            value["qdrant_alias_name"] = qdrant_alias_name
        return value

    def get_active_profile(self) -> EmbeddingProfile:
        self.ensure_bootstrap_state()
        row = self.db.scalar(
            select(EmbeddingProfile).where(EmbeddingProfile.is_active.is_(True)).order_by(EmbeddingProfile.created_at.desc()).limit(1)
        )
        if row is None:
            raise HTTPException(status_code=500, detail="Active embedding profile is missing")
        if row.provider != "openai_api":
            # Compatibility self-heal for previous local-provider deployments. We keep the old profile,
            # create/ensure an OpenAI profile, and mark it active so retrieval/chat remains usable.
            row.is_active = False
            row.status = "retired"
            self.db.flush()
            healed = self.db.scalar(
                select(EmbeddingProfile)
                .where(
                    EmbeddingProfile.provider == "openai_api",
                    EmbeddingProfile.model_id == "text-embedding-3-small",
                )
                .order_by(EmbeddingProfile.created_at.desc())
                .limit(1)
            )
            if healed is None:
                healed = EmbeddingProfile(
                    name="openai-text-embedding-3-small-v1",
                    provider="openai_api",
                    model_id="text-embedding-3-small",
                    dimensions=1536,
                    distance_metric="cosine",
                    normalize_embeddings=True,
                    input_prefix_mode="openai_native",
                    qdrant_collection_name=self.settings.qdrant_collection,
                    qdrant_alias_name=DEFAULT_ALIAS_NAME,
                    status="active",
                    is_active=True,
                    validation_status_json={"status": "auto-healed", "reason": "openai_only_mode"},
                )
                self.db.add(healed)
            else:
                healed.is_active = True
                healed.status = "active"
            self.db.flush()
            return healed
        return row

    def get_latest_draft_profile(self) -> EmbeddingProfile | None:
        self.ensure_bootstrap_state()
        return self.db.scalar(
            select(EmbeddingProfile)
            .where(
                EmbeddingProfile.status == "draft",
                EmbeddingProfile.provider == "openai_api",
            )
            .order_by(EmbeddingProfile.updated_at.desc())
            .limit(1)
        )

    def get_profile(self, profile_id: str) -> EmbeddingProfile:
        row = self.db.get(EmbeddingProfile, profile_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Embedding profile not found")
        return row

    def profile_to_dict(self, row: EmbeddingProfile | None) -> dict[str, Any] | None:
        if row is None:
            return None
        validation = row.validation_status_json or {}
        if isinstance(validation, list):
            validation = {"items": validation}
        return {
            "id": row.id,
            "name": row.name,
            "provider": row.provider,
            "model_id": row.model_id,
            "dimensions": row.dimensions,
            "distance_metric": row.distance_metric,
            "normalize_embeddings": row.normalize_embeddings,
            "input_prefix_mode": row.input_prefix_mode,
            "qdrant_collection_name": row.qdrant_collection_name,
            "qdrant_alias_name": row.qdrant_alias_name,
            "status": row.status,
            "is_active": row.is_active,
            "validation_status_json": validation,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _openai_api_key_or_400(self) -> str:
        api_key = self.secrets_service.get_secret("openai_api_key")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key is not configured")
        return api_key

    def _provider_from_config(self, config: dict[str, Any], *, dimension_hint: int | None = None) -> EmbeddingProvider:
        provider = str(config.get("provider", "openai_api"))
        model_id = str(config.get("model_id") or self.settings.embedding_model_id)
        batch_size = int(config.get("batch_size", self.settings.embedding_batch_size))
        input_prefix_mode = str(config.get("input_prefix_mode", "e5"))
        normalize_embeddings = bool(config.get("normalize_embeddings", True))
        if provider != "openai_api":
            raise HTTPException(status_code=400, detail="Only OpenAI embeddings are supported in OpenAI-only mode")
        return OpenAIEmbeddingProvider(
            self._openai_api_key_or_400(),
            model_id=model_id,
            batch_size=batch_size,
            input_prefix_mode=input_prefix_mode,
            cached_dimension=dimension_hint,
        )

    def provider_from_profile(self, profile: EmbeddingProfile) -> EmbeddingProvider:
        if profile.provider != "openai_api":
            raise HTTPException(status_code=400, detail="Active embedding profile is not OpenAI-based")
        config = {
            "provider": profile.provider,
            "model_id": profile.model_id,
            "batch_size": self.get_settings_value().get("batch_size", self.settings.embedding_batch_size),
            "normalize_embeddings": profile.normalize_embeddings,
            "input_prefix_mode": profile.input_prefix_mode,
        }
        return self._provider_from_config(config, dimension_hint=profile.dimensions)

    def validate_embedding_config(self, config: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(self._default_settings_value())
        normalized.update(config or {})
        provider_name = str(normalized["provider"])
        if provider_name != "openai_api":
            raise HTTPException(status_code=400, detail="Only OpenAI embeddings are supported")
        model_id = str(normalized["model_id"])
        warnings: list[str] = []
        provider = self._provider_from_config(normalized)
        health = provider.health()
        if not health.ok:
            raise HTTPException(status_code=400, detail=f"Embedding provider health check failed: {health.detail}")
        try:
            dim = int(provider.dimension())
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Unable to determine embedding dimensions: {exc}") from exc
        if dim <= 0:
            raise HTTPException(status_code=400, detail="Embedding dimension must be positive")
        if provider_name == "openai_api" and normalized.get("input_prefix_mode") == "e5":
            warnings.append("OpenAI embeddings usually do not require E5 prefixes; consider `openai_native`.")
        return {
            "ok": True,
            "provider": provider_name,
            "model_id": model_id,
            "dimensions": dim,
            "detail": health.detail or "ok",
            "warnings": warnings,
            "metadata": {"health_metadata": health.metadata},
            "normalized_config": normalized,
        }

    def update_embedding_settings(self, payload: dict[str, Any], actor_user_id: str | None) -> dict[str, Any]:
        self.ensure_bootstrap_state()
        validation = self.validate_embedding_config(payload)
        normalized = validation["normalized_config"]
        row = self._ensure_settings_row()
        row.value_json = {k: normalized[k] for k in self._default_settings_value().keys()}
        row.version += 1
        row.updated_by_user_id = actor_user_id
        self.db.flush()

        draft_profile = None
        if bool(payload.get("create_draft_profile", True)):
            draft_profile = self._create_or_update_draft_profile(
                normalized_config=normalized,
                validation=validation,
                actor_user_id=actor_user_id,
            )
        return {
            "settings_row": row,
            "validation": validation,
            "active_profile": self.get_active_profile(),
            "latest_draft_profile": draft_profile or self.get_latest_draft_profile(),
        }

    def _create_or_update_draft_profile(
        self,
        *,
        normalized_config: dict[str, Any],
        validation: dict[str, Any],
        actor_user_id: str | None,
    ) -> EmbeddingProfile:
        provider = str(normalized_config["provider"])
        model_id = str(normalized_config["model_id"])
        dim = int(validation["dimensions"])
        alias_name = str(normalized_config.get("qdrant_alias_name") or DEFAULT_ALIAS_NAME)
        existing = self.db.scalar(
            select(EmbeddingProfile)
            .where(
                EmbeddingProfile.status == "draft",
                EmbeddingProfile.provider == provider,
                EmbeddingProfile.model_id == model_id,
                EmbeddingProfile.dimensions == dim,
            )
            .order_by(EmbeddingProfile.updated_at.desc())
            .limit(1)
        )
        if existing is None:
            count_for_model = int(
                self.db.scalar(
                    select(func.count()).select_from(EmbeddingProfile).where(
                        EmbeddingProfile.provider == provider, EmbeddingProfile.model_id == model_id
                    )
                )
                or 0
            )
            existing = EmbeddingProfile(
                name=f"{provider}-{_slugify_model(model_id)}-v{count_for_model + 1}",
                provider=provider,
                model_id=model_id,
                dimensions=dim,
                distance_metric=str(normalized_config.get("distance_metric", "cosine")),
                normalize_embeddings=bool(normalized_config.get("normalize_embeddings", True)),
                input_prefix_mode=str(normalized_config.get("input_prefix_mode", "e5")),
                qdrant_collection_name="",  # assigned when reindex run starts
                qdrant_alias_name=alias_name,
                status="draft",
                is_active=False,
                validation_status_json={},
                created_by_user_id=actor_user_id,
            )
            self.db.add(existing)
        existing.distance_metric = str(normalized_config.get("distance_metric", "cosine"))
        existing.normalize_embeddings = bool(normalized_config.get("normalize_embeddings", True))
        existing.input_prefix_mode = str(normalized_config.get("input_prefix_mode", "e5"))
        existing.qdrant_alias_name = alias_name
        existing.status = "draft"
        existing.is_active = False
        existing.validation_status_json = {
            "status": "validated",
            "validated_at": datetime.now(UTC).isoformat(),
            "warnings": validation.get("warnings", []),
            "detail": validation.get("detail"),
        }
        existing.updated_by_user_id = actor_user_id
        self.db.flush()
        return existing

    def get_active_alias_name(self) -> str:
        settings_value = self.get_settings_value()
        return str(settings_value.get("qdrant_alias_name") or DEFAULT_ALIAS_NAME)

    def _collection_vector_size(self, collection_name: str) -> int | None:
        try:
            info = self.qdrant.get_collection(collection_name)
        except Exception:  # noqa: BLE001
            return None
        try:
            vectors_cfg = info.config.params.vectors  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            return None
        direct_size = getattr(vectors_cfg, "size", None)
        if direct_size is not None:
            try:
                return int(direct_size)
            except Exception:  # noqa: BLE001
                return None
        if isinstance(vectors_cfg, dict):
            for value in vectors_cfg.values():
                maybe_size = getattr(value, "size", None)
                if maybe_size is None and isinstance(value, dict):
                    maybe_size = value.get("size")
                if maybe_size is not None:
                    try:
                        return int(maybe_size)
                    except Exception:  # noqa: BLE001
                        continue
        return None

    def _ensure_active_alias_dimension_matches_profile(self, alias_name: str, target_collection: str | None) -> None:
        if not target_collection:
            return
        active_profile = self.db.scalar(
            select(EmbeddingProfile)
            .where(EmbeddingProfile.is_active.is_(True))
            .order_by(EmbeddingProfile.created_at.desc())
            .limit(1)
        )
        if active_profile is None:
            return
        required_dim = int(active_profile.dimensions or 0)
        if required_dim <= 0:
            return
        current_dim = self._collection_vector_size(target_collection)
        if current_dim is None or current_dim == required_dim:
            return

        candidate = active_profile.qdrant_collection_name or self.settings.qdrant_collection
        candidate_dim = self._collection_vector_size(candidate) if candidate else None
        if candidate == target_collection or (candidate_dim is not None and candidate_dim != required_dim):
            candidate = f"{self.settings.qdrant_collection}__dim_{required_dim}"
            candidate_dim = self._collection_vector_size(candidate)
        if candidate_dim != required_dim:
            self.ensure_collection(
                candidate,
                size=required_dim,
                distance_metric=active_profile.distance_metric,
            )

        self.switch_alias(alias_name=alias_name, new_collection=candidate)
        active_profile.qdrant_collection_name = candidate
        validation = dict(active_profile.validation_status_json or {})
        validation["alias_auto_healed"] = {
            "previous_target": target_collection,
            "previous_dim": current_dim,
            "new_target": candidate,
            "required_dim": required_dim,
            "at": datetime.now(UTC).isoformat(),
        }
        active_profile.validation_status_json = validation
        self.db.flush()

    def get_active_collection_alias_or_name(self) -> str:
        alias_name = self.get_active_alias_name()
        target = self.get_alias_target(alias_name)
        if target:
            self._ensure_active_alias_dimension_matches_profile(alias_name, target)
            return alias_name
        # Legacy fallback for earlier deployments without alias.
        if self.qdrant.collection_exists(self.settings.qdrant_collection):
            self.ensure_alias_bootstrap(alias_name=alias_name, fallback_collection=self.settings.qdrant_collection)
            target = self.get_alias_target(alias_name)
            if target:
                self._ensure_active_alias_dimension_matches_profile(alias_name, target)
                return alias_name
            return self.settings.qdrant_collection
        return alias_name

    def ensure_collection(self, collection_name: str, *, size: int, distance_metric: str = "cosine") -> None:
        requested_name = collection_name
        alias_target = self.get_alias_target(collection_name)
        if alias_target:
            collection_name = alias_target
        else:
            # In OpenAI-only mode the active write path often uses the alias name. If the alias
            # is missing (fresh environment), create the underlying collection instead of a
            # concrete collection named like the alias.
            try:
                active_alias = self.get_active_alias_name()
            except Exception:  # noqa: BLE001
                active_alias = DEFAULT_ALIAS_NAME
            if collection_name == active_alias:
                try:
                    active_profile = self.get_active_profile()
                    collection_name = active_profile.qdrant_collection_name or self.settings.qdrant_collection
                except Exception:  # noqa: BLE001
                    collection_name = self.settings.qdrant_collection

        try:
            exists = self.qdrant.collection_exists(collection_name)
        except Exception:  # noqa: BLE001
            exists = False
        if exists:
            if requested_name != collection_name:
                try:
                    self.ensure_alias_bootstrap(alias_name=requested_name, fallback_collection=collection_name)
                except Exception:  # noqa: BLE001
                    pass
            return
        dist = qmodels.Distance.COSINE if distance_metric.lower() == "cosine" else qmodels.Distance.COSINE
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=int(size), distance=dist),
        )
        if requested_name != collection_name:
            try:
                self.ensure_alias_bootstrap(alias_name=requested_name, fallback_collection=collection_name)
            except Exception:  # noqa: BLE001
                # Alias creation is best-effort; read path can self-heal later.
                pass

    def get_alias_target(self, alias_name: str) -> str | None:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{self.qdrant_http_base}/aliases")
            resp.raise_for_status()
            data = resp.json()
            aliases = (((data or {}).get("result") or {}).get("aliases")) or []
            for item in aliases:
                if item.get("alias_name") == alias_name:
                    return str(item.get("collection_name"))
        except Exception:  # noqa: BLE001
            return None
        return None

    def ensure_alias_bootstrap(self, *, alias_name: str, fallback_collection: str) -> None:
        target = self.get_alias_target(alias_name)
        if target:
            return
        try:
            if not self.qdrant.collection_exists(fallback_collection):
                return
            self._apply_alias_actions(
                [{"create_alias": {"collection_name": fallback_collection, "alias_name": alias_name}}]
            )
        except Exception:  # noqa: BLE001
            # Alias bootstrap is best-effort to avoid breaking startup.
            return

    def switch_alias(self, *, alias_name: str, new_collection: str) -> str:
        current = self.get_alias_target(alias_name)
        actions: list[dict[str, Any]] = []
        if current:
            actions.append({"delete_alias": {"alias_name": alias_name}})
        actions.append({"create_alias": {"collection_name": new_collection, "alias_name": alias_name}})
        self._apply_alias_actions(actions)
        return new_collection

    def _apply_alias_actions(self, actions: list[dict[str, Any]]) -> None:
        with httpx.Client(timeout=20) as client:
            resp = client.post(f"{self.qdrant_http_base}/collections/aliases", json={"actions": actions})
        resp.raise_for_status()

    def mark_profile_active(self, *, profile: EmbeddingProfile, actor_user_id: str | None) -> None:
        for row in self.db.scalars(select(EmbeddingProfile).where(EmbeddingProfile.is_active.is_(True))).all():
            row.is_active = False
            row.status = "retired"
            row.updated_by_user_id = actor_user_id
        profile.is_active = True
        profile.status = "active"
        profile.updated_by_user_id = actor_user_id
        self.db.flush()

    def status_payload(self) -> dict[str, Any]:
        self.ensure_bootstrap_state()
        alias_name = self.get_active_alias_name()
        latest_run = self.db.scalar(select(EmbeddingReindexRun).order_by(EmbeddingReindexRun.created_at.desc()).limit(1))
        reindex_summary: dict[str, Any] = {}
        if latest_run:
            total = int(
                self.db.scalar(
                    select(func.count()).select_from(EmbeddingReindexRunItem).where(EmbeddingReindexRunItem.run_id == latest_run.id)
                )
                or 0
            )
            reindex_summary = {
                "latest_run_id": latest_run.id,
                "latest_run_status": latest_run.status,
                "latest_run_total_items": total,
                "latest_run_finished_at": latest_run.finished_at,
            }
        return {
            "active_alias_name": alias_name,
            "active_alias_target": self.get_alias_target(alias_name),
            "active_profile": self.profile_to_dict(self.get_active_profile()),
            "latest_draft_profile": self.profile_to_dict(self.get_latest_draft_profile()),
            "settings": self.get_settings_value(),
            "openai_key_status": self.secrets_service.get_secret_status("openai_api_key"),
            "reindex_summary": reindex_summary,
        }
