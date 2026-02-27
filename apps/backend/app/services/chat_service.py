from __future__ import annotations

from datetime import UTC, datetime
import time
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ChatMessage, ChatSession, Document, ModelUsageLog, User
from app.providers.interfaces import InferenceRequest
from app.rag.citations.citation_utils import build_citations_from_retrieval, infer_answer_mode
from app.rag.prompts.prompt_builder import build_context_prompt, build_rag_system_prompt
from app.services.provider_service import ProviderService
from app.services.project_access_service import ProjectAccessService
from app.services.retrieval_service import RetrievalService
from app.services.settings_service import SettingsService


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.provider_service = ProviderService(db)
        self.retrieval_service = RetrievalService(db)
        self.settings_service = SettingsService(db)
        self.project_access_service = ProjectAccessService(db)

    def _get_or_create_session(self, *, user: User, session_id: str | None, project_id: str | None) -> ChatSession:
        if session_id:
            existing = self.db.get(ChatSession, session_id)
            if existing and existing.user_id == user.id and not existing.is_archived:
                if existing.project_id:
                    self.project_access_service.require_project_role(
                        project_id=existing.project_id,
                        user=user,
                        minimum_role="viewer",
                        allow_inactive_project=True,
                    )
                return existing
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required when creating a new chat session")
        self.project_access_service.require_project_role(
            project_id=project_id,
            user=user,
            minimum_role="viewer",
            allow_inactive_project=True,
        )
        session = ChatSession(user_id=user.id, project_id=project_id, title="New Chat")
        self.db.add(session)
        self.db.flush()
        return session

    def _next_message_index(self, session_id: str) -> int:
        current = self.db.scalar(
            select(func.max(ChatMessage.message_index)).where(ChatMessage.session_id == session_id)
        )
        return (int(current) if current is not None else -1) + 1

    def _persist_message(
        self,
        *,
        session_id: str,
        user_id: str | None,
        project_id_snapshot: str | None = None,
        project_name_snapshot: str | None = None,
        role: str,
        content: str,
        index: int,
        **meta,  # noqa: ANN003
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            message_index=index,
            project_id_snapshot=project_id_snapshot,
            project_name_snapshot=project_name_snapshot,
            **meta,
        )
        self.db.add(msg)
        self.db.flush()
        return msg

    def ask(
        self,
        *,
        current_user: User,
        question: str,
        session_id: str | None = None,
        project_id: str | None = None,
        document_ids: list[str] | None = None,
        provider_override: str | None = None,
    ) -> dict[str, Any]:
        session = self._get_or_create_session(user=current_user, session_id=session_id, project_id=project_id)
        if not session.project_id:
            raise HTTPException(status_code=400, detail="Chat session is missing project scope")
        project, _membership = self.project_access_service.require_project_role(
            project_id=session.project_id,
            user=current_user,
            minimum_role="viewer",
            allow_inactive_project=True,
        )
        if document_ids:
            rows = list(
                self.db.scalars(
                    select(Document)
                    .where(Document.id.in_(document_ids), Document.deleted_at.is_(None))
                ).all()
            )
            row_ids = {r.id for r in rows}
            missing = [doc_id for doc_id in document_ids if doc_id not in row_ids]
            if missing:
                raise HTTPException(status_code=404, detail="One or more documents were not found")
            wrong_scope = [r.id for r in rows if r.project_id != session.project_id]
            if wrong_scope:
                raise HTTPException(status_code=403, detail="document_ids must belong to the same project as the chat session")
        user_idx = self._next_message_index(session.id)
        self._persist_message(
            session_id=session.id,
            user_id=current_user.id,
            role="user",
            content=question,
            index=user_idx,
            project_id_snapshot=session.project_id,
            project_name_snapshot=project.name,
        )

        rag_defaults = self.settings_service.get_namespace("rag", "defaults").value_json
        top_k = int((rag_defaults or {}).get("top_k", self.settings.rag_top_k))
        min_score = float((rag_defaults or {}).get("min_score", self.settings.rag_min_score))
        answer_behavior_mode = str(
            (rag_defaults or {}).get("answer_behavior_mode", self.settings.rag_answer_behavior_mode)
        )
        strict_mode = answer_behavior_mode == "strict_rag_only"

        retrieved = self.retrieval_service.retrieve(
            question=question,
            project_id=session.project_id,
            top_k=top_k,
            document_ids=document_ids,
        )
        strong_retrieved = [r for r in retrieved if float(r.get("score") or 0.0) >= min_score]
        has_context = len(strong_retrieved) > 0
        citations = build_citations_from_retrieval(strong_retrieved)

        active_provider = "openai_api"
        _ = provider_override  # OpenAI-only mode
        resolved_model_id = self.provider_service.resolve_chat_model()

        if not has_context and strict_mode:
            answer_text = "No relevant context was found in the indexed documents, so I cannot answer from retrieved docs."
            answer_mode = infer_answer_mode(has_context=False, strict_mode=True)
            latency_ms = 0
            usage = {}
        else:
            system_prompt = build_rag_system_prompt(answer_behavior_mode)
            prompt = build_context_prompt(question, strong_retrieved if strong_retrieved else retrieved)
            history_rows = list(
                self.db.scalars(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session.id)
                    .order_by(ChatMessage.message_index.asc())
                    .limit(20)
                ).all()
            )
            conversation = [
                {"role": row.role, "content": row.content}
                for row in history_rows
                if row.role in {"user", "assistant"} and row.content
            ][-10:]
            provider = self.provider_service.get_inference_provider(active_provider)
            started = time.perf_counter()
            result = provider.generate(
                InferenceRequest(
                    model_id=resolved_model_id,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    conversation=conversation[:-1] if conversation else [],
                    temperature=0.2,
                    metadata={"project_id": session.project_id},
                )
            )
            latency_ms = result.latency_ms or int((time.perf_counter() - started) * 1000)
            answer_text = result.text
            usage = result.usage
            answer_mode = infer_answer_mode(has_context=has_context, strict_mode=strict_mode)

        assistant_idx = self._next_message_index(session.id)
        assistant_msg = self._persist_message(
            session_id=session.id,
            user_id=None,
            role="assistant",
            content=answer_text,
            index=assistant_idx,
            project_id_snapshot=session.project_id,
            project_name_snapshot=project.name,
            provider=active_provider,
            provider_model_id=resolved_model_id,
            model_category=None,
            answer_mode=answer_mode,
            citations_json=citations,
            retrieval_metadata_json={"retrieved_count": len(retrieved), "strong_retrieved_count": len(strong_retrieved)},
            token_usage_json=usage,
            latency_ms=latency_ms,
            status="ok",
        )
        session.last_message_at = datetime.now(UTC)

        usage_log = ModelUsageLog(
            user_id=current_user.id,
            context_type="chat",
            context_id=assistant_msg.id,
            provider=active_provider,
            model_id=resolved_model_id,
            model_category=None,
            latency_ms=latency_ms,
            prompt_tokens=(usage or {}).get("prompt_tokens"),
            completion_tokens=(usage or {}).get("completion_tokens"),
            total_tokens=(usage or {}).get("total_tokens"),
            estimated_cost_usd=None,
            status="ok",
        )
        self.db.add(usage_log)
        self.db.flush()

        return {
            "answer": answer_text,
            "citations": citations,
            "provider": active_provider,
            "resolved_model_id": resolved_model_id,
            "answer_mode": answer_mode,
            "latency_ms": latency_ms,
            "usage": usage,
            "session_id": session.id,
            "message_id": assistant_msg.id,
            "project_id": session.project_id,
        }

    def list_sessions(self, *, user_id: str, include_archived: bool = False) -> tuple[list[ChatSession], int]:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(ChatSession.is_archived.is_(False))
        items = list(
            self.db.scalars(
                stmt.order_by(ChatSession.updated_at.desc())
            ).all()
        )
        return items, len(items)

    def create_session(self, *, user: User, title: str, project_id: str) -> ChatSession:
        self.project_access_service.require_project_role(project_id=project_id, user=user, minimum_role="viewer", allow_inactive_project=True)
        session = ChatSession(user_id=user.id, project_id=project_id, title=title)
        self.db.add(session)
        self.db.flush()
        return session

    def list_messages(self, *, session_id: str, user_id: str) -> tuple[list[ChatMessage], int]:
        session = self.db.get(ChatSession, session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if session.project_id:
            user = self.db.get(User, user_id)
            if user:
                self.project_access_service.require_project_role(
                    project_id=session.project_id,
                    user=user,
                    minimum_role="viewer",
                    allow_inactive_project=True,
                )
        items = list(
            self.db.scalars(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.message_index.asc())
            ).all()
        )
        return items, len(items)

    def delete_session(self, *, session_id: str, user_id: str) -> ChatSession:
        session = self.db.get(ChatSession, session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if session.project_id:
            user = self.db.get(User, user_id)
            if user:
                self.project_access_service.require_project_role(
                    project_id=session.project_id,
                    user=user,
                    minimum_role="viewer",
                    allow_inactive_project=True,
                )
        session.is_archived = True
        self.db.flush()
        return session
