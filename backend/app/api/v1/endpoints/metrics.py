import json
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import require_active_user, require_workspace_role
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.intelligence import MetricDefinition, MetricVersion
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.intelligence import (
    MetricCalculateRequest,
    MetricCalculateResponse,
    MetricCreateRequest,
    MetricResponse,
    MetricUpdateRequest,
    MetricValidateRequest,
    MetricValidateResponse,
    MetricVersionResponse,
)
from app.services.intelligence.metric_engine import MetricIntelligenceEngine

router = APIRouter(prefix="/metrics", tags=["Business Metric Intelligence"])


@router.get("", response_model=list[MetricResponse])
async def list_metrics(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[MetricResponse]:
    workspace, _ = ws_context
    stmt = select(MetricDefinition).where(MetricDefinition.workspace_id == workspace.id)
    if dataset_id:
        stmt = stmt.where(
            (MetricDefinition.dataset_id == dataset_id) | (MetricDefinition.dataset_id.is_(None))
        )
    stmt = stmt.order_by(MetricDefinition.created_at.desc())
    res = await db.execute(stmt)
    metrics = res.scalars().all()
    return [MetricResponse.model_validate(m) for m in metrics]


@router.post("", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def create_metric(
    req: MetricCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetricResponse:
    workspace, _ = ws_context
    metric = await MetricIntelligenceEngine.create_metric(
        workspace_id=workspace.id,
        dataset_id=req.dataset_id,
        name=req.name,
        description=req.description,
        formula=req.formula,
        aggregation=req.aggregation,
        formatting=req.formatting,
        source_columns=req.source_columns,
        owner_id=current_user.id,
        db=db,
    )
    await db.commit()
    await db.refresh(metric)
    return MetricResponse.model_validate(metric)


@router.get("/{metric_id}", response_model=MetricResponse)
async def get_metric(
    metric_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetricResponse:
    workspace, _ = ws_context
    stmt = select(MetricDefinition).where(
        MetricDefinition.id == metric_id,
        MetricDefinition.workspace_id == workspace.id,
    )
    metric = (await db.execute(stmt)).scalar_one_or_none()
    if not metric:
        raise DataLensException("Metric definition not found.", code="NOT_FOUND")
    return MetricResponse.model_validate(metric)


@router.patch("/{metric_id}", response_model=MetricResponse)
async def update_metric(
    metric_id: uuid.UUID,
    req: MetricUpdateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetricResponse:
    workspace, _ = ws_context
    stmt = select(MetricDefinition).where(
        MetricDefinition.id == metric_id,
        MetricDefinition.workspace_id == workspace.id,
    )
    metric = (await db.execute(stmt)).scalar_one_or_none()
    if not metric:
        raise DataLensException("Metric definition not found.", code="NOT_FOUND")

    updates = req.model_dump(exclude_unset=True)
    change_summary = updates.pop("change_summary", None)
    updated = await MetricIntelligenceEngine.update_metric(
        metric=metric,
        updates=updates,
        user_id=current_user.id,
        change_summary=change_summary,
        db=db,
    )
    await db.commit()
    await db.refresh(updated)
    return MetricResponse.model_validate(updated)


@router.delete("/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_metric(
    metric_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace, _ = ws_context
    stmt = select(MetricDefinition).where(
        MetricDefinition.id == metric_id,
        MetricDefinition.workspace_id == workspace.id,
    )
    metric = (await db.execute(stmt)).scalar_one_or_none()
    if not metric:
        raise DataLensException("Metric definition not found.", code="NOT_FOUND")
    await db.delete(metric)
    await db.commit()


@router.get("/{metric_id}/versions", response_model=list[MetricVersionResponse])
async def get_metric_versions(
    metric_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MetricVersionResponse]:
    workspace, _ = ws_context
    # Check parent exists
    parent_stmt = select(MetricDefinition).where(
        MetricDefinition.id == metric_id,
        MetricDefinition.workspace_id == workspace.id,
    )
    parent = (await db.execute(parent_stmt)).scalar_one_or_none()
    if not parent:
        raise DataLensException("Metric definition not found.", code="NOT_FOUND")

    stmt = (
        select(MetricVersion)
        .where(MetricVersion.metric_id == metric_id)
        .order_by(MetricVersion.version_number.desc())
    )
    versions = (await db.execute(stmt)).scalars().all()
    return [MetricVersionResponse.model_validate(v) for v in versions]


@router.post("/validate", response_model=MetricValidateResponse)
async def validate_metric_formula(
    req: MetricValidateRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
) -> MetricValidateResponse:
    is_valid, refs, errors = MetricIntelligenceEngine.validate_formula(
        formula=req.formula,
        available_columns=req.available_columns,
    )
    compiled = MetricIntelligenceEngine.compile_formula_to_sql(req.formula) if is_valid else None
    return MetricValidateResponse(
        is_valid=is_valid,
        referenced_columns=refs,
        errors=errors,
        compiled_sql=compiled,
    )


@router.post("/calculate", response_model=MetricCalculateResponse)
async def calculate_metric(
    req: MetricCalculateRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetricCalculateResponse:
    workspace, _ = ws_context
    # Resolve dataset & files
    stmt = select(Dataset).where(
        Dataset.id == req.dataset_id,
        Dataset.workspace_id == workspace.id,
        Dataset.is_archived.is_(False),
    )
    dataset = (await db.execute(stmt)).scalar_one_or_none()
    if not dataset or not dataset.current_version_id:
        raise DataLensException("Dataset not found or has no active version.", code="NOT_FOUND")

    ver_stmt = select(DatasetVersion).where(DatasetVersion.id == dataset.current_version_id)
    version = (await db.execute(ver_stmt)).scalar_one_or_none()
    if not version:
        raise DataLensException("Dataset version not found.", code="NOT_FOUND")

    storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
    manifest_path = storage_root / version.storage_key
    if not manifest_path.is_file():
        raise DataLensException("Dataset manifest not found on disk.", code="STORAGE_NOT_FOUND")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parquet_paths = [storage_root / p for p in manifest.get("parts", [])]

    result = MetricIntelligenceEngine.calculate_metric_value(
        formula=req.formula,
        aggregation=req.aggregation,
        parquet_files=parquet_paths,
        source_columns=[],
    )

    return MetricCalculateResponse(
        metric_value=result["metric_value"],
        is_null=result["is_null"],
        formula=result["formula"],
        compiled_sql=result["compiled_sql"],
    )

