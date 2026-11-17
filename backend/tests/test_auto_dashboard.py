"""Comprehensive unit and integration tests for AI Auto Dashboard Generator."""

import uuid
from pathlib import Path

import duckdb
import pytest

from app.schemas.auto_dashboard import (
    AutoDashboardStage,
)
from app.services.dashboards.auto_generator import (
    AutoDashboardSessionManager,
    DashboardAnalyticsExecutor,
    DatasetIntelligenceResolver,
    DeterministicDashboardPlanner,
)


@pytest.fixture
def sample_sales_parquet(tmp_path: Path) -> Path:
    pq_path = tmp_path / "sales_sample.parquet"
    con = duckdb.connect(":memory:")
    con.execute(f"""
        CREATE TABLE sales AS
        SELECT
            'ORD-' || lpad(i::VARCHAR, 4, '0') as order_id,
            'CUST-' || (i % 5 + 1)::VARCHAR as customer_id,
            CASE i % 3
                WHEN 0 THEN 'Electronics'
                WHEN 1 THEN 'Furniture'
                ELSE 'Office Supplies'
            END as category,
            CASE i % 4
                WHEN 0 THEN 'North'
                WHEN 1 THEN 'South'
                WHEN 2 THEN 'East'
                ELSE 'West'
            END as region,
            (50 + (i * 13.5))::DOUBLE as amount,
            (i % 5 + 1)::INT as quantity,
            DATE '2025-01-01' + INTERVAL (i * 3) DAY as order_date
        FROM range(1, 51) t(i);
        COPY sales TO '{pq_path.as_posix()}' (FORMAT PARQUET);
    """)
    con.close()
    return pq_path


@pytest.fixture
def sample_hr_parquet(tmp_path: Path) -> Path:
    pq_path = tmp_path / "hr_sample.parquet"
    con = duckdb.connect(":memory:")
    con.execute(f"""
        CREATE TABLE hr AS
        SELECT
            'EMP-' || lpad(i::VARCHAR, 4, '0') as emp_id,
            CASE i % 3
                WHEN 0 THEN 'Engineering'
                WHEN 1 THEN 'Marketing'
                ELSE 'Finance'
            END as department,
            (50000 + (i * 1200))::DOUBLE as salary,
            CASE i % 2 WHEN 0 THEN 'Active' ELSE 'On Leave' END as status,
            DATE '2024-01-01' + INTERVAL (i * 5) DAY as hire_date
        FROM range(1, 31) t(i);
        COPY hr TO '{pq_path.as_posix()}' (FORMAT PARQUET);
    """)
    con.close()
    return pq_path


def test_deterministic_planner_sales_domain():
    profile = {
        "row_count": 50,
        "columns": [
            {"name": "order_id", "candidate_pk": True, "physical_type": "VARCHAR"},
            {"name": "category", "is_dimension": True, "physical_type": "VARCHAR"},
            {"name": "region", "is_dimension": True, "physical_type": "VARCHAR"},
            {"name": "amount", "is_measure": True, "physical_type": "DOUBLE", "semantic_type": "currency"},
            {"name": "quantity", "is_measure": True, "physical_type": "INT"},
            {"name": "order_date", "logical_type": "date", "physical_type": "DATE"},
        ],
    }

    plan = DeterministicDashboardPlanner.plan_dashboard(
        profile=profile,
        business_domain="sales",
        user_objective="Analyze revenue trends by region and product category",
        theme="ocean",
        dataset_name="Quarterly Sales",
    )

    assert "Sales" in plan["title"]
    assert len(plan["kpis"]) >= 3
    kpi_cols = [k["metric_column"] for k in plan["kpis"]]
    assert "amount" in kpi_cols
    assert "order_id" in kpi_cols or "*" in kpi_cols

    chart_types = [c["widget_type"] for c in plan["charts"]]
    assert "line" in chart_types or "area" in chart_types
    assert "donut" in chart_types or "bar" in chart_types
    assert "table" in chart_types


def test_deterministic_planner_hr_domain():
    profile = {
        "row_count": 30,
        "columns": [
            {"name": "emp_id", "candidate_pk": True, "physical_type": "VARCHAR"},
            {"name": "department", "is_dimension": True, "physical_type": "VARCHAR"},
            {"name": "salary", "is_measure": True, "physical_type": "DOUBLE"},
            {"name": "status", "is_dimension": True, "physical_type": "VARCHAR"},
            {"name": "hire_date", "logical_type": "date", "physical_type": "DATE"},
        ],
    }

    plan = DeterministicDashboardPlanner.plan_dashboard(
        profile=profile,
        business_domain="hr",
        user_objective=None,
        theme="forest",
        dataset_name="Employees",
    )

    assert "Workforce" in plan["title"] or "Employees" in plan["title"]
    assert any(k["metric_column"] == "salary" for k in plan["kpis"])
    assert any(c["query_config"].get("group_by_column") == "department" for c in plan["charts"])


def test_analytics_executor_calculates_real_duckdb_results(sample_sales_parquet: Path):
    plan = {
        "title": "Sales Executive Dashboard",
        "theme": "ocean",
        "kpis": [
            {"title": "Total Revenue", "metric_column": "amount", "aggregation": "sum"},
            {"title": "Average Order", "metric_column": "amount", "aggregation": "avg"},
            {"title": "Unique Orders", "metric_column": "order_id", "aggregation": "distinct_count"},
        ],
        "charts": [
            {
                "widget_type": "line",
                "title": "Monthly Trend",
                "grid_x": 0,
                "grid_y": 3,
                "grid_w": 7,
                "grid_h": 6,
                "query_config": {
                    "time_column": "order_date",
                    "metric_column": "amount",
                    "granularity": "month",
                    "aggregation": "sum",
                },
            },
            {
                "widget_type": "donut",
                "title": "Sales by Category",
                "grid_x": 7,
                "grid_y": 3,
                "grid_w": 5,
                "grid_h": 6,
                "query_config": {
                    "group_by_column": "category",
                    "metric_column": "amount",
                    "aggregation": "sum",
                    "limit": 5,
                },
            },
            {
                "widget_type": "table",
                "title": "Top Records",
                "grid_x": 0,
                "grid_y": 9,
                "grid_w": 12,
                "grid_h": 6,
                "query_config": {
                    "columns": ["order_id", "category", "region", "amount"],
                    "limit": 10,
                },
            },
        ],
        "filters": [
            {"name": "Date Range", "column_name": "order_date", "filter_type": "date_range"},
            {"name": "Category", "column_name": "category", "filter_type": "dropdown"},
        ],
    }

    kpis, charts, filters, insights = DashboardAnalyticsExecutor.execute_plan_metrics(
        plan=plan,
        parquet_files=[sample_sales_parquet],
    )

    # 1. Verify KPIs
    assert len(kpis) == 3
    assert kpis[0].numeric_value > 0
    assert kpis[0].formatted_value != ""
    assert kpis[2].numeric_value == 50  # 50 unique orders

    # 2. Verify Line Chart Data
    line_chart = next(c for c in charts if c.widget_type == "line")
    assert line_chart.calculated_data is not None
    assert len(line_chart.calculated_data["labels"]) > 0
    assert len(line_chart.calculated_data["values"]) == len(line_chart.calculated_data["labels"])

    # 3. Verify Donut Chart Data
    donut_chart = next(c for c in charts if c.widget_type == "donut")
    assert donut_chart.calculated_data is not None
    assert len(donut_chart.calculated_data["categories"]) == 3  # Electronics, Furniture, Office Supplies
    assert donut_chart.calculated_data["total"] > 0

    # 4. Verify Insights
    assert len(insights) >= 1
    assert "Leading Segment" in insights[0].title or "Milestone" in insights[0].title
    assert insights[0].evidence != ""


def test_session_manager_lifecycle():
    ws_id = uuid.uuid4()
    ds_id = uuid.uuid4()

    # 1. Create Session
    gen_id = AutoDashboardSessionManager.create_session(
        workspace_id=ws_id,
        dataset_id=ds_id,
        dataset_name="Test Dataset",
    )
    status_resp = AutoDashboardSessionManager.get_status(gen_id, ws_id)
    assert status_resp.generation_id == gen_id
    assert status_resp.status == "running"
    assert status_resp.stage == AutoDashboardStage.READING_STRUCTURE.value

    # 2. Update Session
    AutoDashboardSessionManager.update_session(
        gen_id=gen_id,
        stage=AutoDashboardStage.CALCULATING_RESULTS,
        progress_pct=75,
        message="Calculating metrics...",
    )
    status_updated = AutoDashboardSessionManager.get_status(gen_id, ws_id)
    assert status_updated.progress_pct == 75
    assert status_updated.stage == AutoDashboardStage.CALCULATING_RESULTS.value

    # 3. Cancel Session
    cancel_res = AutoDashboardSessionManager.cancel_session(gen_id, ws_id)
    assert cancel_res["cancelled"] is True
    status_cancelled = AutoDashboardSessionManager.get_status(gen_id, ws_id)
    assert status_cancelled.status == "cancelled"


def test_deterministic_planner_generic_and_edge_datasets():
    # 1. Generic Dataset
    profile_generic = {
        "row_count": 100,
        "columns": [
            {"name": "col_a", "physical_type": "DOUBLE", "is_measure": True},
            {"name": "col_b", "physical_type": "INT", "is_measure": True},
            {"name": "col_c", "physical_type": "VARCHAR", "is_dimension": True},
        ],
    }
    plan_gen = DeterministicDashboardPlanner.plan_dashboard(
        profile=profile_generic,
        business_domain="general",
        user_objective="Analyze general trends",
        theme="monochrome",
        dataset_name="General Data",
    )
    assert len(plan_gen["kpis"]) >= 2
    assert any(c["widget_type"] in ("bar", "donut") for c in plan_gen["charts"])

    # 2. Inventory Dataset Domain
    profile_inv = {
        "row_count": 250,
        "columns": [
            {"name": "sku", "candidate_pk": True, "physical_type": "VARCHAR"},
            {"name": "stock_qty", "is_measure": True, "physical_type": "INT"},
            {"name": "warehouse", "is_dimension": True, "physical_type": "VARCHAR"},
        ],
    }
    detected = DatasetIntelligenceResolver.detect_business_domain(profile_inv, None)
    assert detected == "inventory"

    # 3. Customer Dataset Domain
    profile_cust = {
        "row_count": 400,
        "columns": [
            {"name": "customer_id", "candidate_pk": True, "physical_type": "VARCHAR"},
            {"name": "revenue", "is_measure": True, "physical_type": "DOUBLE"},
            {"name": "country", "is_dimension": True, "physical_type": "VARCHAR"},
        ],
    }
    detected_cust = DatasetIntelligenceResolver.detect_business_domain(profile_cust, None)
    assert detected_cust in ("sales", "customer")


@pytest.mark.asyncio
async def test_auto_dashboard_api_endpoints_status_and_cancel():
    from httpx import ASGITransport, AsyncClient

    from app.dependencies.auth import get_current_workspace, require_active_user
    from app.main import app
    from app.models.user import User
    from app.models.workspace import Workspace

    ws_id = uuid.uuid4()
    ds_id = uuid.uuid4()
    test_user = User(id=uuid.uuid4(), email="test@datalens.ai", full_name="Test User", is_active=True)
    test_ws = Workspace(id=ws_id, name="Test WS", owner_id=test_user.id)

    app.dependency_overrides[require_active_user] = lambda: test_user
    app.dependency_overrides[get_current_workspace] = lambda: (test_ws, "owner")

    gen_id = AutoDashboardSessionManager.create_session(
        workspace_id=ws_id,
        dataset_id=ds_id,
        dataset_name="API Test Dataset",
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Check status
            res = await client.get(
                f"/api/v1/dashboards/auto-generate/{gen_id}",
                headers={"X-Workspace-ID": str(ws_id)},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["generation_id"] == str(gen_id)
            assert data["dataset_name"] == "API Test Dataset"

            # 2. Cancel session
            cancel_res = await client.post(
                f"/api/v1/dashboards/auto-generate/{gen_id}/cancel",
                headers={"X-Workspace-ID": str(ws_id)},
            )
            assert cancel_res.status_code == 200
            assert cancel_res.json()["cancelled"] is True
    finally:
        app.dependency_overrides.clear()

