import json
import time
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import (
    require_workspace_role,
)
from app.models.analysis_run import AnalysisRun
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.workspace import Workspace
from app.services.analytics.engine import AnalyticsEngine
from app.services.analytics.schemas import (
    AggregationRequest,
    AggregationResponse,
    AnalysisRunCreateRequest,
    AnalysisRunResponse,
    ComparisonRequest,
    ComparisonResponse,
    DatasetProfileResponse,
    DescriptiveStatsRequest,
    DescriptiveStatsResponse,
    QualityReportResponse,
    TimeSeriesRequest,
    TimeSeriesResponse,
)

router = APIRouter(prefix="/datasets/{dataset_id}", tags=["Analytics"])


async def _resolve_dataset_and_parts(
    dataset_id: uuid.UUID,
    workspace_id: uuid.UUID,
    version_id: uuid.UUID | None,
    db: AsyncSession,
) -> tuple[Dataset, DatasetVersion, list[Path], list[dict]]:
    stmt = (
        select(Dataset)
        .options(
            selectinload(Dataset.versions),
            selectinload(Dataset.current_version),
        )
        .where(
            Dataset.id == dataset_id,
            Dataset.workspace_id == workspace_id,
            Dataset.is_archived.is_(False),
        )
    )
    res = await db.execute(stmt)
    dataset = res.scalar_one_or_none()
    if not dataset:
        raise DataLensException("Dataset not found in this workspace.", code="NOT_FOUND")

    target_ver_id = version_id or dataset.current_version_id
    if not target_ver_id:
        raise DataLensException("Dataset has no active version to analyze.", code="NOT_FOUND")

    ver_stmt = select(DatasetVersion).where(
        DatasetVersion.id == target_ver_id,
        DatasetVersion.dataset_id == dataset.id,
    )
    version = (await db.execute(ver_stmt)).scalar_one_or_none()
    if not version:
        raise DataLensException("Dataset version not found.", code="NOT_FOUND")

    storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
    manifest_path = storage_root / version.storage_key
    if not manifest_path.is_file():
        raise DataLensException("Dataset manifest not found on disk.", code="STORAGE_NOT_FOUND")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parquet_paths = [storage_root / p for p in manifest.get("parts", [])]
    columns_meta = manifest.get("columns", [])

    return dataset, version, parquet_paths, columns_meta


@router.post("/analytics/profile", response_model=DatasetProfileResponse)
async def get_dataset_profile(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
) -> DatasetProfileResponse:
    workspace, _ = ws_context
    dataset, version, parquet_paths, columns_meta = await _resolve_dataset_and_parts(
        dataset_id, workspace.id, version_id, db
    )
    return AnalyticsEngine.compute_profiling(
        parquet_files=parquet_paths,
        columns_meta=columns_meta,
        dataset_id=dataset.id,
        version_id=str(version.id),
    )


@router.post("/analytics/summary", response_model=DescriptiveStatsResponse)
async def get_descriptive_stats(
    dataset_id: uuid.UUID,
    req: DescriptiveStatsRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DescriptiveStatsResponse:
    workspace, _ = ws_context
    _, version, parquet_paths, columns_meta = await _resolve_dataset_and_parts(
        dataset_id, workspace.id, req.version_id, db
    )
    return AnalyticsEngine.compute_descriptive_stats(
        parquet_files=parquet_paths,
        columns_meta=columns_meta,
        target_columns=req.columns,
        filters=req.filters,
        version_id=str(version.id),
    )


@router.post("/analytics/aggregate", response_model=AggregationResponse)
async def get_aggregation(
    dataset_id: uuid.UUID,
    req: AggregationRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AggregationResponse:
    workspace, _ = ws_context
    _, version, parquet_paths, _ = await _resolve_dataset_and_parts(
        dataset_id, workspace.id, req.version_id, db
    )
    return AnalyticsEngine.compute_aggregation(
        parquet_files=parquet_paths,
        group_by_columns=req.group_by_columns,
        metric_column=req.metric_column,
        aggregation=req.aggregation,
        sort_order=req.sort_order,
        limit=req.limit,
        filters=req.filters,
        version_id=str(version.id),
    )


@router.post("/analytics/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    dataset_id: uuid.UUID,
    req: TimeSeriesRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TimeSeriesResponse:
    workspace, _ = ws_context
    _, version, parquet_paths, _ = await _resolve_dataset_and_parts(
        dataset_id, workspace.id, req.version_id, db
    )
    return AnalyticsEngine.compute_time_series(
        parquet_files=parquet_paths,
        date_column=req.date_column,
        value_column=req.value_column,
        interval=req.interval,
        aggregation=req.aggregation,
        filters=req.filters,
        version_id=str(version.id),
    )


@router.post("/analytics/quality", response_model=QualityReportResponse)
async def get_data_quality(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query()] = None,
) -> QualityReportResponse:
    workspace, _ = ws_context
    _, version, parquet_paths, columns_meta = await _resolve_dataset_and_parts(
        dataset_id, workspace.id, version_id, db
    )
    return AnalyticsEngine.compute_data_quality(
        parquet_files=parquet_paths,
        columns_meta=columns_meta,
        version_id=str(version.id),
    )


@router.post("/analytics/compare", response_model=ComparisonResponse)
async def compare_dataset_versions(
    dataset_id: uuid.UUID,
    req: ComparisonRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ComparisonResponse:
    workspace, _ = ws_context
    _, base_ver, base_paths, _ = await _resolve_dataset_and_parts(
        dataset_id, workspace.id, req.baseline_version_id, db
    )
    _, comp_ver, comp_paths, _ = await _resolve_dataset_and_parts(
        dataset_id, workspace.id, req.compare_version_id, db
    )
    return AnalyticsEngine.compare_versions(
        baseline_files=base_paths,
        compare_files=comp_paths,
        baseline_ver_num=base_ver.version_number,
        compare_ver_num=comp_ver.version_number,
        metric_columns=req.metric_columns,
    )


# ==========================================
# ANALYSIS RUNS PERSISTENCE
# ==========================================

@router.post("/analysis-runs", response_model=AnalysisRunResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis_run(
    dataset_id: uuid.UUID,
    req: AnalysisRunCreateRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisRunResponse:
    workspace, _ = ws_context
    dataset, version, parquet_paths, columns_meta = await _resolve_dataset_and_parts(
        dataset_id, workspace.id, req.version_id, db
    )

    start_time = time.perf_counter()
    res_summary: dict[str, Any] = {}

    if req.analysis_type == "profile":
        prof = AnalyticsEngine.compute_profiling(parquet_paths, columns_meta, dataset.id, str(version.id))
        res_summary = prof.model_dump(mode="json")
    elif req.analysis_type == "quality":
        qual = AnalyticsEngine.compute_data_quality(parquet_paths, columns_meta, str(version.id))
        res_summary = qual.model_dump(mode="json")
    elif req.analysis_type == "aggregate":
        agg = AnalyticsEngine.compute_aggregation(
            parquet_files=parquet_paths,
            group_by_columns=req.parameters.get("group_by_columns", []),
            metric_column=req.parameters.get("metric_column"),
            aggregation=req.parameters.get("aggregation", "count"),
            sort_order=req.parameters.get("sort_order", "desc"),
            limit=req.parameters.get("limit", 50),
            filters=None,
            version_id=str(version.id),
        )
        res_summary = agg.model_dump(mode="json")
    else:  # summary default
        stats = AnalyticsEngine.compute_descriptive_stats(parquet_paths, columns_meta, None, None, str(version.id))
        res_summary = stats.model_dump(mode="json")

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    run = AnalysisRun(
        id=uuid.uuid4(),
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        analysis_type=req.analysis_type,
        parameters=req.parameters,
        result_summary=res_summary,
        status="completed",
        execution_time_ms=duration_ms,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return AnalysisRunResponse.model_validate(run)


@router.get("/analysis-runs", response_model=list[AnalysisRunResponse])
async def list_analysis_runs(
    dataset_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AnalysisRunResponse]:
    workspace, _ = ws_context
    # Verify dataset belongs to workspace
    stmt = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.workspace_id == workspace.id,
        Dataset.is_archived.is_(False),
    )
    ds = (await db.execute(stmt)).scalar_one_or_none()
    if not ds:
        raise DataLensException("Dataset not found in this workspace.", code="NOT_FOUND")

    run_stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.dataset_id == dataset_id)
        .order_by(desc(AnalysisRun.created_at))
    )
    runs = (await db.execute(run_stmt)).scalars().all()
    return [AnalysisRunResponse.model_validate(r) for r in runs]


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunResponse)
async def get_analysis_run_detail(
    dataset_id: uuid.UUID,
    run_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisRunResponse:
    workspace, _ = ws_context
    stmt = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.workspace_id == workspace.id,
        Dataset.is_archived.is_(False),
    )
    ds = (await db.execute(stmt)).scalar_one_or_none()
    if not ds:
        raise DataLensException("Dataset not found in this workspace.", code="NOT_FOUND")

    run_stmt = select(AnalysisRun).where(
        AnalysisRun.id == run_id,
        AnalysisRun.dataset_id == dataset_id,
    )
    run = (await db.execute(run_stmt)).scalar_one_or_none()
    if not run:
        raise DataLensException("Analysis run not found.", code="NOT_FOUND")
    return AnalysisRunResponse.model_validate(run)
