from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.embedding_provider_service import EmbeddingProviderService


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.embedding_provider_service = EmbeddingProviderService(db)
        self.qdrant = QdrantClient(host=self.settings.qdrant_host, port=self.settings.qdrant_port)

    def retrieve(
        self,
        *,
        question: str,
        project_id: str,
        top_k: int | None = None,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        profile = self.embedding_provider_service.get_active_profile()
        embedding_provider = self.embedding_provider_service.provider_from_profile(profile)
        query_vec = embedding_provider.embed_texts([question], input_kind="query").vectors[0]
        collection_name = self.embedding_provider_service.get_active_collection_alias_or_name()
        must_conditions: list[qmodels.FieldCondition] = [
            qmodels.FieldCondition(
                key="project_id",
                match=qmodels.MatchValue(value=project_id),
            )
        ]
        if document_ids:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchAny(any=document_ids),
                )
            )
        filt = qmodels.Filter(must=must_conditions)
        try:
            if hasattr(self.qdrant, "query_points"):
                response = self.qdrant.query_points(
                    collection_name=collection_name,
                    query=query_vec,
                    limit=top_k or self.settings.rag_top_k,
                    query_filter=filt,
                    with_payload=True,
                    with_vectors=False,
                )
                results = list(getattr(response, "points", []) or [])
            else:
                # Compatibility path for older qdrant-client versions.
                results = self.qdrant.search(  # type: ignore[attr-defined]
                    collection_name=collection_name,
                    query_vector=query_vec,
                    limit=top_k or self.settings.rag_top_k,
                    query_filter=filt,
                    with_payload=True,
                )
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "Retrieval search failed",
                extra={
                    "event": "retrieval.search_failed",
                    "project_id": project_id,
                    "collection_name": collection_name,
                    "error": str(exc),
                },
            )
            return []

        items: list[dict[str, Any]] = []
        for point in results:
            payload = point.payload or {}
            items.append(
                {
                    "document_id": payload.get("document_id"),
                    "filename": payload.get("filename"),
                    "chunk_id": payload.get("chunk_id"),
                    "text": payload.get("text") or payload.get("text_excerpt") or "",
                    "page": payload.get("source_page"),
                    "score": float(point.score or 0.0),
                    "project_id": payload.get("project_id"),
                }
            )
        return items
