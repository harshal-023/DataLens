import json
import uuid
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.dashboard import Dashboard, DashboardWidget
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership


@pytest.mark.asyncio
async def test_advanced_visualization_queries(tmp_path):
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with session_maker() as session:
            user = User(
                full_name="Vis User",
                email=f"vis_user_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            ws = Workspace(name="Vis Workspace", owner_id=user.id)
            session.add(ws)
            await session.commit()
            await session.refresh(ws)

            session.add(WorkspaceMembership(workspace_id=ws.id, user_id=user.id, role="owner"))
            await session.commit()

            # Create test dataset with rich metrics
            storage_root = Path(settings.STORAGE_ROOT).resolve()
            ds_id = uuid.uuid4()
            ver_id = uuid.uuid4()
            rel_dir = f"datasets/{ws.id}/{ds_id}/{ver_id}/processed"
            (storage_root / rel_dir).mkdir(parents=True, exist_ok=True)

            parquet_path = storage_root / rel_dir / "part_0.parquet"
            data_table = pa.Table.from_pydict({
                "region": ["North", "North", "South", "South", "East", "West"],
                "category": ["Tech", "Furniture", "Tech", "Furniture", "Tech", "Furniture"],
                "sales": [1200.0, 450.0, 950.0, 600.0, 1500.0, 300.0],
                "profit": [300.0, -50.0, 200.0, 80.0, 450.0, 20.0],
                "order_date": ["2026-01-15", "2026-02-10", "2026-03-05", "2026-04-12", "2026-05-20", "2026-06-18"],
            })
            pq.write_table(data_table, parquet_path)

            manifest_data = {
                "parts": [f"{rel_dir}/part_0.parquet"],
                "row_count": 6,
                "column_count": 5,
                "columns": [
                    {"name": "region", "inferred_type": "string"},
                    {"name": "category", "inferred_type": "string"},
                    {"name": "sales", "inferred_type": "float"},
                    {"name": "profit", "inferred_type": "float"},
                    {"name": "order_date", "inferred_type": "date"},
                ],
            }
            (storage_root / rel_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

            dataset = Dataset(
                id=ds_id,
                workspace_id=ws.id,
                uploaded_by=user.id,
                name="Sales & Profit Master",
                original_filename="sales.parquet",
                file_type="parquet",
                row_count=6,
                column_count=5,
                status="ready",
                is_archived=False,
            )
            session.add(dataset)
            await session.flush()

            version = DatasetVersion(
                id=ver_id,
                dataset_id=ds_id,
                version_number="v1",
                storage_key=f"{rel_dir}/manifest.json",
                original_storage_key=f"{rel_dir}/manifest.json",
                file_size=parquet_path.stat().st_size,
                schema_metadata={"columns": manifest_data["columns"]},
                row_count=6,
                column_count=5,
                status="ready",
            )
            session.add(version)
            await session.flush()
            dataset.current_version_id = version.id

            # Create test Dashboard
            dashboard = Dashboard(
                workspace_id=ws.id,
                created_by=user.id,
                title="Advanced Analytics Dashboard",
            )
            session.add(dashboard)
            await session.flush()

            # Create Widgets for different advanced types:
            # 1. Stacked Bar
            w_stacked = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=ds_id,
                dataset_version_id=ver_id,
                widget_type="stacked_bar",
                title="Sales by Region and Category",
                query_config={
                    "group_by_column": "region",
                    "sub_group_by_column": "category",
                    "metric_column": "sales",
                    "aggregation": "sum",
                },
            )

            # 2. Histogram
            w_hist = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=ds_id,
                dataset_version_id=ver_id,
                widget_type="histogram",
                title="Sales Distribution",
                query_config={
                    "metric_column": "sales",
                    "bins": 5,
                },
            )

            # 3. Box Plot
            w_box = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=ds_id,
                dataset_version_id=ver_id,
                widget_type="box_plot",
                title="Sales Box Plot by Region",
                query_config={
                    "group_by_column": "region",
                    "metric_column": "sales",
                },
            )

            # 4. Correlation
            w_corr = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=ds_id,
                dataset_version_id=ver_id,
                widget_type="correlation",
                title="Sales vs Profit Correlation",
                query_config={
                    "columns": ["sales", "profit"],
                },
            )

            # 5. Pareto
            w_pareto = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=ds_id,
                dataset_version_id=ver_id,
                widget_type="pareto",
                title="Regional Sales Pareto Analysis",
                query_config={
                    "group_by_column": "region",
                    "metric_column": "sales",
                },
            )

            # 6. Gauge with Target Comparison
            w_gauge = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=ds_id,
                dataset_version_id=ver_id,
                widget_type="gauge",
                title="Annual Revenue Target",
                query_config={
                    "metric_column": "sales",
                    "target_value": 4000.0,
                },
            )

            # 7. Drill-Down Widget
            w_drill = DashboardWidget(
                dashboard_id=dashboard.id,
                dataset_id=ds_id,
                dataset_version_id=ver_id,
                widget_type="bar",
                title="Hierarchical Drill Widget",
                query_config={
                    "hierarchy_levels": ["region", "category"],
                    "metric_column": "sales",
                },
            )

            session.add_all([w_stacked, w_hist, w_box, w_corr, w_pareto, w_gauge, w_drill])
            await session.commit()
            await session.refresh(w_stacked)
            await session.refresh(w_hist)
            await session.refresh(w_box)
            await session.refresh(w_corr)
            await session.refresh(w_pareto)
            await session.refresh(w_gauge)
            await session.refresh(w_drill)

        token = create_access_token(user.id, user.email)
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws.id)}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Test Stacked Bar Query
            q1 = await ac.post(
                f"/api/v1/dashboards/{dashboard.id}/widgets/{w_stacked.id}/query",
                headers=headers,
                json={},
            )
            assert q1.status_code == 200
            d1 = q1.json()["data"]
            assert "categories" in d1
            assert "series" in d1
            assert len(d1["series"]) == 2  # Furniture and Tech

            # 2. Test Histogram Query
            q2 = await ac.post(
                f"/api/v1/dashboards/{dashboard.id}/widgets/{w_hist.id}/query",
                headers=headers,
                json={},
            )
            assert q2.status_code == 200
            d2 = q2.json()["data"]
            assert "bins" in d2
            assert len(d2["bins"]) == 5

            # 3. Test Box Plot Query
            q3 = await ac.post(
                f"/api/v1/dashboards/{dashboard.id}/widgets/{w_box.id}/query",
                headers=headers,
                json={},
            )
            assert q3.status_code == 200
            d3 = q3.json()["data"]
            assert "items" in d3
            first_box = d3["items"][0]
            assert "median" in first_box
            assert "q1" in first_box
            assert "q3" in first_box

            # 4. Test Correlation Matrix Query
            q4 = await ac.post(
                f"/api/v1/dashboards/{dashboard.id}/widgets/{w_corr.id}/query",
                headers=headers,
                json={},
            )
            assert q4.status_code == 200
            d4 = q4.json()["data"]
            assert d4["columns"] == ["sales", "profit"]
            assert d4["matrix"][0][0] == 1.0  # diagonal is 1.0

            # 5. Test Pareto Chart Query
            q5 = await ac.post(
                f"/api/v1/dashboards/{dashboard.id}/widgets/{w_pareto.id}/query",
                headers=headers,
                json={},
            )
            assert q5.status_code == 200
            d5 = q5.json()["data"]
            assert "items" in d5
            assert "cumulative_pct" in d5["items"][0]

            # 6. Test Gauge & Comparison
            q6 = await ac.post(
                f"/api/v1/dashboards/{dashboard.id}/widgets/{w_gauge.id}/query",
                headers=headers,
                json={"target_value": 4000.0},
            )
            assert q6.status_code == 200
            d6 = q6.json()["data"]
            assert d6["target"] == 4000.0
            assert d6["value"] == 5000.0
            assert d6["percent_of_target"] == 125.0

            # 7. Test Hierarchical Drill-Down Query
            # Level 0: Group by Region
            q7_l0 = await ac.post(
                f"/api/v1/dashboards/{dashboard.id}/widgets/{w_drill.id}/query",
                headers=headers,
                json={"drill_level": 0},
            )
            assert q7_l0.status_code == 200
            d7_l0 = q7_l0.json()
            assert d7_l0["data"]["group_by"] == "region"
            assert d7_l0["metadata"]["current_drill_depth"] == 0

            # Level 1: Drill into Category with filter region == "North"
            q7_l1 = await ac.post(
                f"/api/v1/dashboards/{dashboard.id}/widgets/{w_drill.id}/query",
                headers=headers,
                json={
                    "drill_level": 1,
                    "drill_filters": [{"column": "region", "operator": "eq", "value": "North"}],
                },
            )
            assert q7_l1.status_code == 200
            d7_l1 = q7_l1.json()
            assert d7_l1["data"]["group_by"] == "category"
            assert d7_l1["metadata"]["current_drill_depth"] == 1
            # North has Tech (1200) and Furniture (450)
            assert len(d7_l1["data"]["items"]) == 2

    finally:
        app.dependency_overrides.clear()

