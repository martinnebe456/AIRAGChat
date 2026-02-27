from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.models import User
from app.db.models.enums import RoleEnum
from app.db.session import get_db
from app.schemas.evals import (
    EvalCompareResponse,
    EvalDatasetImportRequest,
    EvalDatasetListResponse,
    EvalDatasetResponse,
    EvalRunCreateRequest,
    EvalRunItemListResponse,
    EvalRunItemResponse,
    EvalRunListResponse,
    EvalRunResponse,
)
from app.services.audit_service import AuditService
from app.services.evaluation_service import EvaluationService

router = APIRouter()


def _ds_resp(ds) -> EvalDatasetResponse:  # noqa: ANN001
    return EvalDatasetResponse(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        status=ds.status,
        version=ds.version,
        source_format=ds.source_format,
        item_count=ds.item_count,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


def _run_resp(run) -> EvalRunResponse:  # noqa: ANN001
    return EvalRunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        status=run.status,
        provider=run.provider,
        model_category=run.model_category,
        resolved_model_id=run.resolved_model_id,
        config_snapshot_json=run.config_snapshot_json or {},
        error_summary=run.error_summary,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.get("/datasets", response_model=EvalDatasetListResponse)
def list_datasets(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalDatasetListResponse:
    items, total = EvaluationService(db).list_datasets()
    return EvalDatasetListResponse(items=[_ds_resp(i) for i in items], total=total)


@router.post("/datasets/import", response_model=EvalDatasetResponse)
def import_dataset(
    payload: EvalDatasetImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalDatasetResponse:
    ds = EvaluationService(db).import_dataset(
        name=payload.name,
        description=payload.description,
        source_format=payload.source_format,
        items=payload.items,
        created_by_user_id=admin.id,
    )
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="eval.dataset.import",
        entity_type="evaluation_dataset",
        entity_id=ds.id,
        request=request,
    )
    db.commit()
    return _ds_resp(ds)


@router.get("/datasets/{dataset_id}", response_model=EvalDatasetResponse)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalDatasetResponse:
    return _ds_resp(EvaluationService(db).get_dataset(dataset_id))


@router.patch("/datasets/{dataset_id}", response_model=EvalDatasetResponse)
def patch_dataset(
    dataset_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalDatasetResponse:
    # Minimal implementation: mark archived via PATCH.
    ds = EvaluationService(db).archive_dataset(dataset_id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="eval.dataset.patch",
        entity_type="evaluation_dataset",
        entity_id=ds.id,
        request=request,
    )
    db.commit()
    return _ds_resp(ds)


@router.delete("/datasets/{dataset_id}", response_model=EvalDatasetResponse)
def delete_dataset(
    dataset_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalDatasetResponse:
    ds = EvaluationService(db).archive_dataset(dataset_id)
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="eval.dataset.archive",
        entity_type="evaluation_dataset",
        entity_id=ds.id,
        request=request,
    )
    db.commit()
    return _ds_resp(ds)


@router.get("/datasets/{dataset_id}/items")
def list_dataset_items(
    dataset_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> dict:
    items, total = EvaluationService(db).list_dataset_items(dataset_id)
    return {
        "items": [
            {
                "id": i.id,
                "dataset_id": i.dataset_id,
                "case_key": i.case_key,
                "question": i.question,
                "expected_answer": i.expected_answer,
                "expected_sources_json": i.expected_sources_json,
                "expects_refusal": i.expects_refusal,
                "metadata_json": i.metadata_json,
                "tags_json": i.tags_json,
                "created_at": i.created_at.isoformat(),
                "updated_at": i.updated_at.isoformat(),
            }
            for i in items
        ],
        "total": total,
    }


@router.post("/runs", response_model=EvalRunResponse)
def create_eval_run(
    payload: EvalRunCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalRunResponse:
    run = EvaluationService(db).create_run(
        dataset_id=payload.dataset_id,
        provider=payload.provider,
        model_category=payload.model_category,
        rag_overrides=payload.rag_overrides,
        started_by_user_id=admin.id,
    )
    AuditService(db).log(
        actor_user_id=admin.id,
        action_type="eval.run.create",
        entity_type="evaluation_run",
        entity_id=run.id,
        request=request,
    )
    db.commit()
    return _run_resp(run)


@router.get("/runs", response_model=EvalRunListResponse)
def list_runs(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalRunListResponse:
    items, total = EvaluationService(db).list_runs()
    return EvalRunListResponse(items=[_run_resp(i) for i in items], total=total)


@router.get("/runs/{run_id}", response_model=EvalRunResponse)
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalRunResponse:
    return _run_resp(EvaluationService(db).get_run(run_id))


@router.get("/runs/{run_id}/items", response_model=EvalRunItemListResponse)
def list_run_items(
    run_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalRunItemListResponse:
    items, total = EvaluationService(db).list_run_items(run_id)
    return EvalRunItemListResponse(
        items=[
            EvalRunItemResponse(
                id=i.id,
                run_id=i.run_id,
                status=i.status,
                question=i.question,
                answer_text=i.answer_text,
                metrics_json=i.metrics_json,
                latency_ms=i.latency_ms,
                created_at=i.created_at,
            )
            for i in items
        ],
        total=total,
    )


@router.get("/compare", response_model=EvalCompareResponse)
def compare_runs(
    run_a: str = Query(...),
    run_b: str = Query(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
) -> EvalCompareResponse:
    data = EvaluationService(db).compare_runs(run_a, run_b)
    return EvalCompareResponse(
        run_a=_run_resp(data["run_a"]),
        run_b=_run_resp(data["run_b"]),
        deltas=data["deltas"],
    )
