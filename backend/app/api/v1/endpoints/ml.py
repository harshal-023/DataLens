import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import (
    require_active_user,
    require_workspace_role,
)
from app.models.model_run import ModelRun
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.ml import (
    AnomalyDetectRequest,
    AnomalyDetectResponse,
    ForecastRequest,
    ForecastResponse,
    GenerateInsightRequest,
    InsightResponse,
    ModelRunDetailResponse,
    ModelRunListItem,
    SegmentationRequest,
    SegmentationResponse,
)
from app.services.ml.anomaly import AnomalyDetectionService
from app.services.ml.clustering import SegmentationService
from app.services.ml.data_loader import DatasetDataLoader
from app.services.ml.forecasting import ForecastingService
from app.services.ml.insights import BusinessInsightEngine
from app.services.reports.ml_report_service import MLReportService

router = APIRouter(prefix="/ml", tags=["Advanced Analytics & Machine Learning"])


@router.post("/anomaly", response_model=AnomalyDetectResponse, status_code=status.HTTP_200_OK)
async def detect_anomalies(
    payload: AnomalyDetectRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnomalyDetectResponse:
    """
    Detects statistical anomalies across a numerical column using Z-score, IQR, or Isolation Forest.
    """
    workspace, _ = ws_context
    start_time = time.perf_counter()

    # 1. Load dataset records from Parquet
    cols_to_load = [payload.target_column]
    if payload.time_column:
        cols_to_load.append(payload.time_column)

    dataset, version, records, _ = await DatasetDataLoader.load_version_data(
        db=db,
        dataset_id=payload.dataset_id,
        version_id=payload.version_id,
        workspace_id=workspace.id,
        columns=cols_to_load,
    )

    # 2. Extract and validate numerical series
    series = DatasetDataLoader.extract_numeric_series(
        records=records,
        target_column=payload.target_column,
        time_column=payload.time_column,
        min_rows=5,
    )

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # 3. Create ModelRun entity to track execution provenance
    model_run = ModelRun(
        workspace_id=workspace.id,
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        model_type="anomaly_detection",
        algorithm=payload.algorithm,
        parameters={
            "target_column": payload.target_column,
            "time_column": payload.time_column,
            "sensitivity": payload.sensitivity,
        },
        feature_columns=[payload.target_column],
        status="completed",
        created_by=current_user.id,
    )
    db.add(model_run)
    await db.flush()

    # 4. Execute detection algorithm
    response = AnomalyDetectionService.detect_anomalies(
        series_data=series,
        target_column=payload.target_column,
        algorithm=payload.algorithm,
        sensitivity=payload.sensitivity,
        max_anomalies_return=payload.max_anomalies_return,
        model_run_id=model_run.id,
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        duration_ms=duration_ms,
    )

    # 5. Persist results in ModelRun
    model_run.metrics = {
        "anomalies_detected_count": response.anomalies_detected_count,
        "anomaly_percentage": response.anomaly_percentage,
        **response.summary_metrics,
    }
    model_run.result_summary = response.model_dump(mode="json")
    model_run.duration_ms = duration_ms
    await db.commit()

    return response


@router.post("/forecast", response_model=ForecastResponse, status_code=status.HTTP_200_OK)
async def generate_forecast(
    payload: ForecastRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ForecastResponse:
    """
    Generates time-series forecasting with prediction intervals and backtesting evaluation.
    """
    workspace, _ = ws_context
    start_time = time.perf_counter()

    # 1. Load dataset records
    cols_to_load = [payload.target_column, payload.time_column]
    dataset, version, records, _ = await DatasetDataLoader.load_version_data(
        db=db,
        dataset_id=payload.dataset_id,
        version_id=payload.version_id,
        workspace_id=workspace.id,
        columns=cols_to_load,
    )

    # 2. Extract series with timestamps
    series = DatasetDataLoader.extract_numeric_series(
        records=records,
        target_column=payload.target_column,
        time_column=payload.time_column,
        min_rows=6,
    )

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # 3. Create ModelRun entity
    model_run = ModelRun(
        workspace_id=workspace.id,
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        model_type="forecasting",
        algorithm=payload.algorithm,
        parameters={
            "target_column": payload.target_column,
            "time_column": payload.time_column,
            "forecast_horizon": payload.forecast_horizon,
            "confidence_level": payload.confidence_level,
        },
        feature_columns=[payload.target_column],
        status="completed",
        created_by=current_user.id,
    )
    db.add(model_run)
    await db.flush()

    # 4. Execute forecasting service
    response = ForecastingService.generate_forecast(
        series_data=series,
        target_column=payload.target_column,
        time_column=payload.time_column,
        forecast_horizon=payload.forecast_horizon,
        algorithm=payload.algorithm,
        confidence_level=payload.confidence_level,
        seasonality_period=payload.seasonality_period,
        model_run_id=model_run.id,
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        duration_ms=duration_ms,
    )

    # 5. Persist results in ModelRun
    model_run.metrics = response.backtest_metrics
    model_run.result_summary = response.model_dump(mode="json")
    model_run.duration_ms = duration_ms
    await db.commit()

    return response


@router.post("/segmentation", response_model=SegmentationResponse, status_code=status.HTTP_200_OK)
async def segment_dataset(
    payload: SegmentationRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SegmentationResponse:
    """
    Performs clustering (K-Means or Hierarchical) with feature scaling, profiling, and silhouette scoring.
    """
    workspace, _ = ws_context
    start_time = time.perf_counter()

    # 1. Load dataset records
    dataset, version, records, _ = await DatasetDataLoader.load_version_data(
        db=db,
        dataset_id=payload.dataset_id,
        version_id=payload.version_id,
        workspace_id=workspace.id,
        columns=payload.feature_columns,
    )

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # 2. Create ModelRun entity
    model_run = ModelRun(
        workspace_id=workspace.id,
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        model_type="segmentation",
        algorithm=payload.algorithm,
        parameters={
            "cluster_count": payload.cluster_count,
            "scale_features": payload.scale_features,
        },
        feature_columns=payload.feature_columns,
        status="completed",
        created_by=current_user.id,
    )
    db.add(model_run)
    await db.flush()

    # 3. Execute clustering
    response = SegmentationService.segment_dataset(
        records=records,
        feature_columns=payload.feature_columns,
        algorithm=payload.algorithm,
        cluster_count=payload.cluster_count,
        scale_features=payload.scale_features,
        cluster_label_prefix=payload.cluster_label_prefix,
        model_run_id=model_run.id,
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        duration_ms=duration_ms,
    )

    # 4. Persist results in ModelRun
    model_run.metrics = {
        "cluster_count": response.cluster_count,
        "silhouette_score": response.silhouette_score,
        "inertia": response.inertia,
    }
    model_run.result_summary = response.model_dump(mode="json")
    model_run.duration_ms = duration_ms
    await db.commit()

    return response


@router.get("/runs", response_model=list[ModelRunListItem])
async def list_model_runs(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None, description="Filter by dataset ID"),
    model_type: str | None = Query(None, description="Filter by model type (anomaly_detection, forecasting, segmentation)"),
) -> list[ModelRunListItem]:
    """
    Lists persisted model runs for the active workspace.
    """
    workspace, _ = ws_context
    stmt = (
        select(ModelRun)
        .where(ModelRun.workspace_id == workspace.id)
        .order_by(desc(ModelRun.created_at))
    )
    if dataset_id:
        stmt = stmt.where(ModelRun.dataset_id == dataset_id)
    if model_type:
        stmt = stmt.where(ModelRun.model_type == model_type)

    runs = (await db.execute(stmt)).scalars().all()
    return [
        ModelRunListItem(
            id=r.id,
            workspace_id=r.workspace_id,
            dataset_id=r.dataset_id,
            dataset_version_id=r.dataset_version_id,
            model_type=r.model_type,
            algorithm=r.algorithm,
            status=r.status,
            parameters=r.parameters,
            feature_columns=r.feature_columns,
            metrics=r.metrics,
            duration_ms=r.duration_ms,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=ModelRunDetailResponse)
async def get_model_run_detail(
    run_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModelRunDetailResponse:
    """
    Retrieves full execution details and result payload of an ML model run.
    """
    workspace, _ = ws_context
    stmt = select(ModelRun).where(ModelRun.id == run_id, ModelRun.workspace_id == workspace.id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise DataLensException("Model run not found in workspace.", code="NOT_FOUND")

    return ModelRunDetailResponse(
        id=run.id,
        workspace_id=run.workspace_id,
        dataset_id=run.dataset_id,
        dataset_version_id=run.dataset_version_id,
        model_type=run.model_type,
        algorithm=run.algorithm,
        status=run.status,
        parameters=run.parameters,
        feature_columns=run.feature_columns,
        metrics=run.metrics,
        result_summary=run.result_summary,
        duration_ms=run.duration_ms,
        created_at=run.created_at,
    )


@router.post("/runs/{run_id}/insights", response_model=InsightResponse)
async def generate_model_insight(
    run_id: uuid.UUID,
    payload: GenerateInsightRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InsightResponse:
    """
    Generates grounded narrative business interpretations for an ML model run.
    """
    workspace, _ = ws_context
    stmt = select(ModelRun).where(ModelRun.id == run_id, ModelRun.workspace_id == workspace.id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise DataLensException("Model run not found in workspace.", code="NOT_FOUND")

    return await BusinessInsightEngine.generate_insight(
        model_run=run,
        audience=payload.audience,
        include_recommendations=payload.include_recommendations,
    )


@router.get("/runs/{run_id}/report")
async def download_model_run_report(
    run_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Annotated[str, Query(pattern="^(pdf|docx|xlsx|csv)$")] = "pdf",
) -> Response:
    """
    Downloads an analytical report for a completed model run in PDF, DOCX, XLSX, or CSV format.
    """
    workspace, _ = ws_context
    stmt = select(ModelRun).where(ModelRun.id == run_id, ModelRun.workspace_id == workspace.id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise DataLensException("Model run not found in workspace.", code="NOT_FOUND")

    data, media_type, filename = MLReportService.generate_report(run, report_format=format)
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

