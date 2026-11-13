import json
import uuid
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.model_run import ModelRun
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.ml.anomaly import AnomalyDetectionService
from app.services.ml.clustering import SegmentationService
from app.services.ml.forecasting import ForecastingService
from app.services.ml.insights import BusinessInsightEngine
from app.services.reports.ml_report_service import MLReportService
from tests.conftest import POSTGRES_AVAILABLE

# =========================================================================
# 1. ANOMALY DETECTION UNIT TESTS
# =========================================================================

def test_anomaly_zscore_detection():
    # 10 points with a clear positive outlier (100.0) at index 8
    series_data = [
        {"value": 10.0, "time": "2025-01-01"},
        {"value": 10.2, "time": "2025-01-02"},
        {"value": 9.8, "time": "2025-01-03"},
        {"value": 10.1, "time": "2025-01-04"},
        {"value": 10.0, "time": "2025-01-05"},
        {"value": 10.3, "time": "2025-01-06"},
        {"value": 9.9, "time": "2025-01-07"},
        {"value": 10.1, "time": "2025-01-08"},
        {"value": 100.0, "time": "2025-01-09"},  # Extreme spike
        {"value": 10.0, "time": "2025-01-10"},
    ]

    res = AnomalyDetectionService.detect_anomalies(
        series_data=series_data,
        target_column="sales",
        algorithm="z_score",
        sensitivity=2.0,
    )

    assert res.target_column == "sales"
    assert res.algorithm == "z_score"
    assert res.total_records_analyzed == 10
    assert res.anomalies_detected_count == 1
    assert len(res.anomalous_points) == 1
    spike = res.anomalous_points[0]
    assert spike.row_index == 8
    assert spike.actual_value == 100.0
    assert spike.severity in ["medium", "high"]
    assert spike.anomaly_score > 2.0


def test_anomaly_iqr_detection():
    # Regular values around 20, one low outlier (1.0) and one high outlier (95.0)
    values = [20.0, 21.0, 19.5, 20.5, 22.0, 19.0, 20.0, 21.5, 20.2, 1.0, 95.0]
    series_data = [{"value": v, "time": f"2025-01-{i+1:02d}"} for i, v in enumerate(values)]

    res = AnomalyDetectionService.detect_anomalies(
        series_data=series_data,
        target_column="temperature",
        algorithm="iqr",
        sensitivity=1.5,
    )

    assert res.algorithm == "iqr"
    assert res.anomalies_detected_count == 2
    assert "q1" in res.summary_metrics
    assert "q3" in res.summary_metrics
    assert "iqr" in res.summary_metrics


def test_anomaly_isolation_forest():
    # 25 inliers and 2 distinct outliers
    np.random.seed(42)
    inliers = np.random.normal(loc=50.0, scale=2.0, size=25).tolist()
    series_data = [{"value": float(v)} for v in inliers]
    series_data.append({"value": 150.0})  # Outlier
    series_data.append({"value": -30.0})  # Outlier

    res = AnomalyDetectionService.detect_anomalies(
        series_data=series_data,
        target_column="latency",
        algorithm="isolation_forest",
        sensitivity=2.5,
    )

    assert res.algorithm == "isolation_forest"
    assert res.anomalies_detected_count >= 1
    for a in res.anomalous_points:
        assert a.anomaly_score >= 0.0


def test_anomaly_zero_variance():
    # Perfectly flat constant series
    series_data = [{"value": 42.0} for _ in range(12)]
    res = AnomalyDetectionService.detect_anomalies(
        series_data=series_data,
        target_column="constant_metric",
        algorithm="z_score",
        sensitivity=2.5,
    )
    assert res.anomalies_detected_count == 0
    assert res.summary_metrics["std"] == 0.0


def test_anomaly_insufficient_rows():
    series_data = [{"value": 10.0}, {"value": 12.0}]
    with pytest.raises(DataLensException) as exc:
        AnomalyDetectionService.detect_anomalies(
            series_data=series_data,
            target_column="metric",
        )
    assert exc.value.code == "INSUFFICIENT_DATA"


# =========================================================================
# 2. FORECASTING UNIT TESTS
# =========================================================================

def test_forecast_moving_average():
    # 15 historical points
    series_data = [{"value": float(10 + (i % 3)), "timestamp": f"2025-01-{i+1:02d}"} for i in range(15)]
    res = ForecastingService.generate_forecast(
        series_data=series_data,
        target_column="demand",
        time_column="timestamp",
        forecast_horizon=5,
        algorithm="moving_average",
        confidence_level=0.95,
    )

    assert res.algorithm == "moving_average"
    assert res.forecast_horizon == 5
    assert len(res.forecast_points) == 5
    for pt in res.forecast_points:
        assert pt.lower_bound <= pt.forecast_value <= pt.upper_bound
    assert res.backtest_metrics is not None
    assert res.backtest_metrics["mae"] >= 0.0
    assert res.backtest_metrics["rmse"] >= 0.0


def test_forecast_exponential_smoothing():
    series_data = [{"value": float(50 + 2 * i), "timestamp": f"2025-01-{i+1:02d}"} for i in range(20)]
    res = ForecastingService.generate_forecast(
        series_data=series_data,
        target_column="revenue",
        time_column="timestamp",
        forecast_horizon=6,
        algorithm="exponential_smoothing",
        confidence_level=0.90,
    )

    assert res.algorithm == "exponential_smoothing"
    assert len(res.forecast_points) == 6
    assert res.backtest_metrics["mae"] >= 0.0


def test_forecast_seasonal_naive():
    # Weekly seasonality: length 4 pattern repeated 4 times = 16 points
    pattern = [10.0, 15.0, 12.0, 18.0]
    series_data = [{"value": float(pattern[i % 4]), "timestamp": f"2025-01-{i+1:02d}"} for i in range(16)]

    res = ForecastingService.generate_forecast(
        series_data=series_data,
        target_column="traffic",
        time_column="timestamp",
        forecast_horizon=4,
        algorithm="seasonal_naive",
        seasonality_period=4,
        confidence_level=0.95,
    )

    assert res.algorithm == "seasonal_naive"
    assert len(res.forecast_points) == 4
    assert res.forecast_points[0].forecast_value == 10.0
    assert res.forecast_points[1].forecast_value == 15.0


def test_forecast_linear_trend():
    # Perfectly linear: y = 10 + 5 * i
    series_data = [{"value": float(10 + 5 * i), "timestamp": f"2025-01-{i+1:02d}"} for i in range(10)]
    res = ForecastingService.generate_forecast(
        series_data=series_data,
        target_column="growth",
        time_column="timestamp",
        forecast_horizon=3,
        algorithm="linear_trend",
    )

    assert res.algorithm == "linear_trend"
    assert len(res.forecast_points) == 3
    # Step 10: 10 + 5*10 = 60, Step 11: 65, Step 12: 70
    assert pytest.approx(res.forecast_points[0].forecast_value, abs=0.5) == 60.0
    assert pytest.approx(res.forecast_points[1].forecast_value, abs=0.5) == 65.0
    assert pytest.approx(res.forecast_points[2].forecast_value, abs=0.5) == 70.0


def test_forecast_insufficient_history():
    series_data = [{"value": 10.0}, {"value": 20.0}]
    with pytest.raises(DataLensException) as exc:
        ForecastingService.generate_forecast(
            series_data=series_data,
            target_column="growth",
            time_column="timestamp",
            algorithm="linear_trend",
        )
    assert exc.value.code == "INSUFFICIENT_DATA"


# =========================================================================
# 3. SEGMENTATION & CLUSTERING UNIT TESTS
# =========================================================================

def test_segmentation_kmeans_clustering():
    # 3 distinct clusters of 10 points each
    np.random.seed(42)
    c1 = np.random.normal(loc=[10, 10], scale=1.0, size=(10, 2))
    c2 = np.random.normal(loc=[50, 50], scale=1.0, size=(10, 2))
    c3 = np.random.normal(loc=[100, 100], scale=1.0, size=(10, 2))
    data = np.vstack([c1, c2, c3])

    records = [{"feature_a": float(row[0]), "feature_b": float(row[1])} for row in data]

    res = SegmentationService.segment_dataset(
        records=records,
        feature_columns=["feature_a", "feature_b"],
        algorithm="kmeans",
        cluster_count=3,
        scale_features=True,
    )

    assert res.algorithm == "kmeans"
    assert res.cluster_count == 3
    assert res.total_records_clustered == 30
    assert len(res.clusters) == 3
    assert res.silhouette_score is not None
    assert res.silhouette_score > 0.5


def test_segmentation_hierarchical_clustering():
    np.random.seed(42)
    c1 = np.random.normal(loc=[5, 5], scale=0.5, size=(8, 2))
    c2 = np.random.normal(loc=[25, 25], scale=0.5, size=(8, 2))
    data = np.vstack([c1, c2])

    records = [{"x": float(row[0]), "y": float(row[1])} for row in data]

    res = SegmentationService.segment_dataset(
        records=records,
        feature_columns=["x", "y"],
        algorithm="hierarchical",
        cluster_count=2,
    )

    assert res.algorithm == "hierarchical"
    assert res.cluster_count == 2
    assert res.silhouette_score is not None
    assert res.silhouette_score > 0.5


def test_segmentation_prohibited_attribute_exclusion():
    records = [{"sales": 100.0, "gender": "F"}, {"sales": 200.0, "gender": "M"}]
    with pytest.raises(DataLensException) as exc:
        SegmentationService.segment_dataset(
            records=records,
            feature_columns=["sales", "gender"],
            cluster_count=2,
        )
    assert exc.value.code == "ETHICAL_VIOLATION"


def test_segmentation_insufficient_rows():
    records = [{"sales": 100.0, "spend": 50.0}]
    with pytest.raises(DataLensException) as exc:
        SegmentationService.segment_dataset(
            records=records,
            feature_columns=["sales", "spend"],
            cluster_count=3,
        )
    assert exc.value.code == "INSUFFICIENT_DATA"


# =========================================================================
# 4. REPORT GENERATION UNIT TESTS
# =========================================================================

def test_ml_report_service_pdf_generation():
    dummy_run = ModelRun(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        model_type="anomaly_detection",
        algorithm="z_score",
        parameters={"target_column": "sales", "sensitivity": 0.8},
        feature_columns=["sales"],
        metrics={"anomaly_count": 2, "anomaly_percentage": 4.5},
        result_summary={
            "anomalous_points": [
                {"row_index": 5, "actual_value": 1500.0, "expected_value": 100.0, "anomaly_score": 3.95, "severity": "high"},
                {"row_index": 12, "actual_value": 2.0, "expected_value": 100.0, "anomaly_score": 3.12, "severity": "medium"},
            ]
        },
        status="completed",
        duration_ms=45,
    )

    pdf_bytes, mime, filename = MLReportService.generate_report(dummy_run, report_format="pdf")
    assert mime == "application/pdf"
    assert filename.endswith(".pdf")
    assert pdf_bytes.startswith(b"%PDF")


def test_ml_report_service_docx_generation():
    dummy_run = ModelRun(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        model_type="forecasting",
        algorithm="exponential_smoothing",
        parameters={"target_column": "revenue", "forecast_horizon": 3},
        feature_columns=["revenue"],
        metrics={"mae": 12.5, "rmse": 15.2, "mape": 3.8},
        result_summary={
            "forecast_points": [
                {"period_index": 1, "timestamp": "2025-02-01", "forecast_value": 110.0, "lower_bound": 95.0, "upper_bound": 125.0},
                {"period_index": 2, "timestamp": "2025-02-02", "forecast_value": 120.0, "lower_bound": 102.0, "upper_bound": 138.0},
            ]
        },
        status="completed",
        duration_ms=62,
    )

    docx_bytes, mime, filename = MLReportService.generate_report(dummy_run, report_format="docx")
    assert "openxmlformats" in mime
    assert filename.endswith(".docx")
    assert docx_bytes.startswith(b"PK")  # ZIP container header


def test_ml_report_service_xlsx_generation():
    dummy_run = ModelRun(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        model_type="segmentation",
        algorithm="kmeans",
        parameters={"cluster_count": 2},
        feature_columns=["spend", "frequency"],
        metrics={"silhouette_score": 0.72},
        result_summary={
            "clusters": [
                {"cluster_id": 0, "cluster_name": "Segment 1", "record_count": 15, "percentage": 50.0, "characterization": "Moderate spend"},
                {"cluster_id": 1, "cluster_name": "Segment 2", "record_count": 15, "percentage": 50.0, "characterization": "High spend"},
            ]
        },
        status="completed",
        duration_ms=88,
    )

    xlsx_bytes, mime, filename = MLReportService.generate_report(dummy_run, report_format="xlsx")
    assert "spreadsheetml" in mime
    assert filename.endswith(".xlsx")
    assert xlsx_bytes.startswith(b"PK")


def test_ml_report_service_csv_generation():
    dummy_run = ModelRun(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        model_type="anomaly_detection",
        algorithm="z_score",
        parameters={"target_column": "sales"},
        feature_columns=["sales"],
        metrics={"anomalies_detected_count": 1},
        result_summary={
            "anomalous_points": [
                {"row_index": 3, "timestamp": "2025-01-04", "actual_value": 99.0, "expected_value": 10.0, "anomaly_score": 3.9, "severity": "high"}
            ]
        },
        status="completed",
        duration_ms=30,
    )

    csv_bytes, mime, filename = MLReportService.generate_report(dummy_run, report_format="csv")
    assert mime == "text/csv"
    assert filename.endswith(".csv")
    csv_text = csv_bytes.decode("utf-8")
    assert "row_index" in csv_text
    assert "actual_value" in csv_text


# =========================================================================
# 5. BUSINESS INSIGHT ENGINE UNIT TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_business_insight_deterministic_fallback():
    dummy_run = ModelRun(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        model_type="anomaly_detection",
        algorithm="z_score",
        parameters={"target_column": "revenue"},
        feature_columns=["revenue"],
        metrics={"anomalies_detected_count": 3, "anomaly_percentage": 5.0},
        result_summary={"anomalous_points": [], "total_records_analyzed": 60, "anomalies_detected_count": 3, "anomaly_percentage": 5.0, "target_column": "revenue"},
        status="completed",
        duration_ms=40,
    )

    with patch.object(settings, "AI_ENABLED", False):
        insight = await BusinessInsightEngine.generate_insight(dummy_run, audience="executive")
    assert insight.model_run_id == dummy_run.id
    assert len(insight.key_findings) > 0
    assert len(insight.limitations) > 0


# =========================================================================
# 6. LIVE DATABASE & ENDPOINT INTEGRATION TESTS
# =========================================================================

pytest_live = pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="Live PostgreSQL is offline on port 5432",
)


@pytest.mark.asyncio
async def test_ml_endpoints_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # POST anomaly requires auth
        res_anom = await client.post(
            "/api/v1/ml/anomaly",
            json={"dataset_id": str(uuid.uuid4()), "target_column": "sales"},
        )
        assert res_anom.status_code == 401

        # GET runs requires auth
        res_runs = await client.get("/api/v1/ml/runs")
        assert res_runs.status_code == 401


@pytest_live
@pytest.mark.asyncio
async def test_ml_live_end_to_end_and_rbac():
    """
    Live integration test testing:
    1. Dataset and Parquet upload simulation
    2. Anomaly detection execution and ModelRun persistence
    3. Time-series forecasting execution
    4. Segmentation execution
    5. Run listing and detail inspection
    6. Business insight generation
    7. Multi-format report downloads (PDF, DOCX, XLSX, CSV)
    8. RBAC enforcement: Viewer role cannot trigger ML runs
    9. Cross-workspace isolation
    """
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        # Create Owner and Viewer users, Workspace, Dataset, and DatasetVersion
        async with session_maker() as session:
            owner = User(
                full_name="ML Owner",
                email=f"ml_owner_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("ValidPass123!"),
                is_active=True,
            )
            viewer = User(
                full_name="ML Viewer",
                email=f"ml_viewer_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("ValidPass123!"),
                is_active=True,
            )
            session.add_all([owner, viewer])
            await session.flush()

            ws = Workspace(name="ML Test Workspace", owner_id=owner.id)
            session.add(ws)
            await session.flush()

            m_owner = WorkspaceMembership(workspace_id=ws.id, user_id=owner.id, role="owner")
            m_viewer = WorkspaceMembership(workspace_id=ws.id, user_id=viewer.id, role="viewer")
            session.add_all([m_owner, m_viewer])
            await session.flush()

            # Create physical Parquet dataset
            storage_root = Path(settings.STORAGE_ROOT).resolve()
            storage_root.mkdir(parents=True, exist_ok=True)
            part_name = f"ml_part_{uuid.uuid4().hex[:8]}.parquet"
            part_path = storage_root / part_name

            # Create sample dataframe with 20 rows
            records_data = {
                "date": [f"2025-01-{i+1:02d}" for i in range(20)],
                "sales": [100.0 + (i * 10.0) for i in range(19)] + [1500.0],  # Spike at index 19
                "units": [10.0 + (i % 5) for i in range(20)],
                "spend": [50.0 + (i * 5.0) for i in range(20)],
            }
            arrow_table = pa.Table.from_pydict(records_data)
            pq.write_table(arrow_table, part_path)

            # Create manifest
            manifest = {
                "dataset_name": "ML Sales Data",
                "row_count": 20,
                "parts": [part_name],
                "columns": [
                    {"name": "date", "inferred_type": "string"},
                    {"name": "sales", "inferred_type": "numeric"},
                    {"name": "units", "inferred_type": "numeric"},
                    {"name": "spend", "inferred_type": "numeric"},
                ],
            }
            manifest_key = f"manifest_{uuid.uuid4().hex[:8]}.json"
            (storage_root / manifest_key).write_text(json.dumps(manifest), encoding="utf-8")

            dataset = Dataset(
                workspace_id=ws.id,
                name="ML Sales Data",
                original_filename="sales.csv",
                file_type="csv",
                row_count=20,
                column_count=4,
            )
            session.add(dataset)
            await session.flush()

            version = DatasetVersion(
                dataset_id=dataset.id,
                version_number="v1",
                row_count=20,
                column_count=4,
                storage_key=manifest_key,
                schema_metadata=manifest,
            )
            session.add(version)
            await session.flush()

            dataset.current_version_id = version.id
            await session.commit()

            owner_id = owner.id
            owner_email = owner.email
            viewer_id = viewer.id
            viewer_email = viewer.email
            ws_id = ws.id
            ds_id = dataset.id
            ver_id = version.id

        owner_token = create_access_token(owner_id, owner_email)
        viewer_token = create_access_token(viewer_id, viewer_email)

        owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Workspace-ID": str(ws_id)}
        viewer_headers = {"Authorization": f"Bearer {viewer_token}", "X-Workspace-ID": str(ws_id)}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Anomaly Detection execution (Owner)
            resp_anom = await client.post(
                "/api/v1/ml/anomaly",
                headers=owner_headers,
                json={
                    "dataset_id": str(ds_id),
                    "version_id": str(ver_id),
                    "target_column": "sales",
                    "time_column": "date",
                    "algorithm": "z_score",
                    "sensitivity": 2.0,
                },
            )
            assert resp_anom.status_code == 200, resp_anom.text
            anom_data = resp_anom.json()
            assert anom_data["algorithm"] == "z_score"
            assert anom_data["anomalies_detected_count"] >= 1
            anomaly_run_id = anom_data["model_run_id"]

            # 2. Time-series Forecasting execution (Owner)
            resp_fc = await client.post(
                "/api/v1/ml/forecast",
                headers=owner_headers,
                json={
                    "dataset_id": str(ds_id),
                    "version_id": str(ver_id),
                    "target_column": "sales",
                    "time_column": "date",
                    "algorithm": "exponential_smoothing",
                    "forecast_horizon": 4,
                },
            )
            assert resp_fc.status_code == 200, resp_fc.text
            fc_data = resp_fc.json()
            assert fc_data["algorithm"] == "exponential_smoothing"
            assert len(fc_data["forecast_points"]) == 4
            forecast_run_id = fc_data["model_run_id"]

            # 3. Customer & Business Segmentation execution (Owner)
            resp_seg = await client.post(
                "/api/v1/ml/segmentation",
                headers=owner_headers,
                json={
                    "dataset_id": str(ds_id),
                    "version_id": str(ver_id),
                    "feature_columns": ["units", "spend"],
                    "algorithm": "kmeans",
                    "cluster_count": 2,
                },
            )
            assert resp_seg.status_code == 200, resp_seg.text
            seg_data = resp_seg.json()
            assert seg_data["algorithm"] == "kmeans"
            assert len(seg_data["clusters"]) == 2
            seg_run_id = seg_data["model_run_id"]

            # 4. List Model Runs
            resp_runs = await client.get("/api/v1/ml/runs", headers=owner_headers)
            assert resp_runs.status_code == 200
            run_items = resp_runs.json()
            run_ids = {r["id"] for r in run_items}
            assert anomaly_run_id in run_ids
            assert forecast_run_id in run_ids
            assert seg_run_id in run_ids

            # 5. Get Model Run Detail
            resp_detail = await client.get(f"/api/v1/ml/runs/{anomaly_run_id}", headers=owner_headers)
            assert resp_detail.status_code == 200
            detail_data = resp_detail.json()
            assert detail_data["id"] == anomaly_run_id
            assert detail_data["model_type"] == "anomaly_detection"
            assert "anomalous_points" in detail_data["result_summary"]

            # 6. Generate Business Insights
            resp_insight = await client.post(
                f"/api/v1/ml/runs/{anomaly_run_id}/insights",
                headers=owner_headers,
                json={"audience": "executive", "include_recommendations": True},
            )
            assert resp_insight.status_code == 200
            insight_data = resp_insight.json()
            assert len(insight_data["key_findings"]) > 0

            # 7. Download Reports in PDF, DOCX, XLSX, and CSV
            for fmt, expected_mime in [
                ("pdf", "application/pdf"),
                ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("csv", "text/csv"),
            ]:
                resp_rep = await client.get(
                    f"/api/v1/ml/runs/{anomaly_run_id}/report?format={fmt}",
                    headers=owner_headers,
                )
                assert resp_rep.status_code == 200
                assert expected_mime in resp_rep.headers["content-type"]
                assert len(resp_rep.content) > 0

            # 8. RBAC Verification: Viewer role cannot trigger runs
            resp_viewer_create = await client.post(
                "/api/v1/ml/anomaly",
                headers=viewer_headers,
                json={
                    "dataset_id": str(ds_id),
                    "version_id": str(ver_id),
                    "target_column": "sales",
                },
            )
            assert resp_viewer_create.status_code == 403

            # Viewer CAN view run details and download reports
            resp_viewer_get = await client.get(
                f"/api/v1/ml/runs/{anomaly_run_id}",
                headers=viewer_headers,
            )
            assert resp_viewer_get.status_code == 200

            resp_viewer_dl = await client.get(
                f"/api/v1/ml/runs/{anomaly_run_id}/report?format=pdf",
                headers=viewer_headers,
            )
            assert resp_viewer_dl.status_code == 200

            # 9. Cross-Workspace Isolation: An unauthorized workspace ID cannot access the run
            unauth_ws = uuid.uuid4()
            unauth_headers = {"Authorization": f"Bearer {owner_token}", "X-Workspace-ID": str(unauth_ws)}
            resp_unauth = await client.get(
                f"/api/v1/ml/runs/{anomaly_run_id}",
                headers=unauth_headers,
            )
            # Not a member of unauth_ws -> 403 or 404
            assert resp_unauth.status_code in [403, 404]

    finally:
        app.dependency_overrides.pop(get_db, None)
        await test_engine.dispose()
