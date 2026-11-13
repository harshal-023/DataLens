import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.dashboards.dashboard_export import (
    export_dashboard_csv,
    export_dashboard_pdf,
    export_dashboard_xlsx,
)
from tests.conftest import POSTGRES_AVAILABLE


@pytest.fixture
def mock_db_session(monkeypatch):
    """Isolated session fixture for unit tests."""
    return None


# ---------------------------------------------------------------------------
# Unit Tests for Dashboard Export Generators
# ---------------------------------------------------------------------------

def test_export_dashboard_pdf():
    widget_results = [
        {
            "title": "Revenue KPI",
            "widget_type": "kpi",
            "data": {"metric": "Total Revenue", "value": 150000.0, "formatted_value": "$150,000.00"},
            "row_count": 1,
        },
        {
            "title": "Sales by Category",
            "widget_type": "bar",
            "data": {
                "items": [
                    {"label": "Technology", "value": 80000},
                    {"label": "Furniture", "value": 45000},
                ]
            },
            "row_count": 2,
        },
        {
            "title": "Executive Summary",
            "widget_type": "text",
            "data": {"content": "Q4 performance exceeded targets across all product lines."},
            "row_count": 1,
        },
    ]

    pdf_bytes = export_dashboard_pdf(
        dashboard_title="Q4 Executive Dashboard",
        workspace_name="Acme Corp",
        description="Quarterly performance overview",
        widget_results=widget_results,
        applied_filters=[{"name": "Region", "column": "region", "operator": "eq", "value": "North America"}],
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_export_dashboard_xlsx():
    widget_results = [
        {
            "title": "Sales Breakdown",
            "widget_type": "bar",
            "data": {
                "items": [
                    {"label": "Hardware", "value": 50000},
                    {"label": "Software", "value": 35000},
                ]
            },
            "row_count": 2,
        },
        {
            "title": "Recent Transactions",
            "widget_type": "table",
            "data": {
                "columns": ["id", "customer", "amount"],
                "rows": [
                    {"id": "1", "customer": "Alice", "amount": 120.5},
                    {"id": "2", "customer": "Bob", "amount": 340.0},
                ],
            },
            "row_count": 2,
        },
    ]

    xlsx_bytes = export_dashboard_xlsx(
        dashboard_title="Operations Overview",
        workspace_name="Acme Corp",
        widget_results=widget_results,
    )
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 2000
    # ZIP signature for XLSX
    assert xlsx_bytes[:4] == b"PK\x03\x04"


def test_export_dashboard_csv():
    widget_results = [
        {
            "title": "Sales KPI",
            "widget_type": "kpi",
            "data": {"metric": "Total Sales", "value": 95000},
            "row_count": 1,
        },
        {
            "title": "Customers Table",
            "widget_type": "table",
            "data": {
                "columns": ["customer", "spend"],
                "rows": [{"customer": "Alice", "spend": 500}],
            },
            "row_count": 1,
        },
    ]

    csv_bytes = export_dashboard_csv(
        dashboard_title="Weekly Pulse",
        widget_results=widget_results,
    )
    assert isinstance(csv_bytes, bytes)
    csv_text = csv_bytes.decode("utf-8")
    assert "Weekly Pulse" in csv_text
    assert "Total Sales" in csv_text
    assert "Alice" in csv_text


# ---------------------------------------------------------------------------
# Live PostgreSQL End-to-End & RBAC Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="Live PostgreSQL is offline on port 5432",
)
@pytest.mark.asyncio
async def test_dashboard_crud_and_rbac_live():
    """
    Tests complete Phase 4A lifecycle against live PostgreSQL:
    1. Workspace setup with Owner, Editor, and Viewer
    2. Dashboard creation by Editor
    3. Widget creation & layout configuration
    4. Interactive Filter creation & update
    5. Dashboard duplication
    6. RBAC verification: Viewer cannot modify dashboard or widgets
    7. Cross-workspace isolation: Other workspace cannot access dashboard
    8. Soft-deletion / Archive
    """
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with session_maker() as session:
            # 1. Setup Users
            owner = User(
                full_name="Dashboard Owner",
                email=f"dash_owner_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            editor = User(
                full_name="Dashboard Editor",
                email=f"dash_editor_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            viewer = User(
                full_name="Dashboard Viewer",
                email=f"dash_viewer_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            other_user = User(
                full_name="Other User",
                email=f"other_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            session.add_all([owner, editor, viewer, other_user])
            await session.commit()
            await session.refresh(owner)
            await session.refresh(editor)
            await session.refresh(viewer)
            await session.refresh(other_user)

            # Setup primary workspace
            ws = Workspace(name=f"Analytics Workspace {uuid.uuid4().hex[:6]}", owner_id=owner.id)
            session.add(ws)
            await session.commit()
            await session.refresh(ws)

            # Add memberships
            m_owner = WorkspaceMembership(workspace_id=ws.id, user_id=owner.id, role="owner")
            m_editor = WorkspaceMembership(workspace_id=ws.id, user_id=editor.id, role="editor")
            m_viewer = WorkspaceMembership(workspace_id=ws.id, user_id=viewer.id, role="viewer")
            session.add_all([m_owner, m_editor, m_viewer])

            # Setup isolated foreign workspace
            ws_other = Workspace(name="Foreign Workspace", owner_id=other_user.id)
            session.add(ws_other)
            await session.commit()
            await session.refresh(ws_other)

        owner_token = create_access_token(owner.id, owner.email)
        editor_token = create_access_token(editor.id, editor.email)
        viewer_token = create_access_token(viewer.id, viewer.email)
        other_token = create_access_token(other_user.id, other_user.email)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers_editor = {
                "Authorization": f"Bearer {editor_token}",
                "X-Workspace-Id": str(ws.id),
            }
            headers_viewer = {
                "Authorization": f"Bearer {viewer_token}",
                "X-Workspace-Id": str(ws.id),
            }
            headers_other = {
                "Authorization": f"Bearer {other_token}",
                "X-Workspace-Id": str(ws_other.id),
            }

            # --- A. CREATE DASHBOARD (Editor: OK) ---
            create_res = await client.post(
                "/api/v1/dashboards",
                json={
                    "title": "Executive Performance",
                    "description": "High level KPIs",
                    "visibility": "workspace",
                    "layout_config": {"columns": 12},
                },
                headers=headers_editor,
            )
            assert create_res.status_code == 201, create_res.text
            dash_data = create_res.json()
            dashboard_id = dash_data["id"]
            assert dash_data["title"] == "Executive Performance"

            # --- B. LIST DASHBOARDS (Viewer: OK) ---
            list_res = await client.get("/api/v1/dashboards", headers=headers_viewer)
            assert list_res.status_code == 200
            assert list_res.json()["total"] >= 1

            # --- C. ADD WIDGET (Text Widget: OK) ---
            widget_res = await client.post(
                f"/api/v1/dashboards/{dashboard_id}/widgets",
                json={
                    "widget_type": "text",
                    "title": "Welcome Announcement",
                    "grid_x": 0,
                    "grid_y": 0,
                    "grid_w": 12,
                    "grid_h": 2,
                    "query_config": {"text_content": "Welcome to the Executive Dashboard!"},
                    "display_settings": {"theme": "teal"},
                },
                headers=headers_editor,
            )
            assert widget_res.status_code == 201, widget_res.text
            widget_id = widget_res.json()["id"]

            # --- D. QUERY TEXT WIDGET ---
            query_res = await client.post(
                f"/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}/query",
                json={},
                headers=headers_viewer,
            )
            assert query_res.status_code == 200
            assert query_res.json()["data"]["content"] == "Welcome to the Executive Dashboard!"

            # --- E. ADD & UPDATE FILTER ---
            filter_res = await client.post(
                f"/api/v1/dashboards/{dashboard_id}/filters",
                json={
                    "name": "Region Filter",
                    "column_name": "region",
                    "filter_type": "dropdown",
                    "default_operator": "eq",
                    "default_value": "East",
                },
                headers=headers_editor,
            )
            assert filter_res.status_code == 201
            filter_id = filter_res.json()["id"]

            update_filter_res = await client.put(
                f"/api/v1/dashboards/{dashboard_id}/filters/{filter_id}",
                json={"name": "Regional Zone", "default_value": "West"},
                headers=headers_editor,
            )
            assert update_filter_res.status_code == 200
            assert update_filter_res.json()["name"] == "Regional Zone"

            # --- F. UPDATE LAYOUT ---
            layout_res = await client.post(
                f"/api/v1/dashboards/{dashboard_id}/layout",
                json={
                    "widgets": [
                        {"id": widget_id, "grid_x": 2, "grid_y": 1, "grid_w": 8, "grid_h": 3}
                    ]
                },
                headers=headers_editor,
            )
            assert layout_res.status_code == 200
            updated_widgets = layout_res.json()
            assert updated_widgets[0]["grid_x"] == 2
            assert updated_widgets[0]["grid_w"] == 8

            # --- G. DUPLICATE DASHBOARD ---
            dup_res = await client.post(
                f"/api/v1/dashboards/{dashboard_id}/duplicate",
                headers=headers_editor,
            )
            assert dup_res.status_code == 201
            dup_data = dup_res.json()
            assert "Copy" in dup_data["title"]
            assert len(dup_data["widgets"]) == 1
            assert len(dup_data["filters"]) == 1

            # --- H. RBAC ENFORCEMENT: VIEWER CANNOT CREATE OR MODIFY ---
            viewer_create = await client.post(
                "/api/v1/dashboards",
                json={"title": "Unauthorized Dashboard"},
                headers=headers_viewer,
            )
            assert viewer_create.status_code == 403

            viewer_mod = await client.put(
                f"/api/v1/dashboards/{dashboard_id}",
                json={"title": "Hacked Title"},
                headers=headers_viewer,
            )
            assert viewer_mod.status_code == 403

            viewer_del = await client.delete(
                f"/api/v1/dashboards/{dashboard_id}",
                headers=headers_viewer,
            )
            assert viewer_del.status_code == 403

            # --- I. CROSS-WORKSPACE ISOLATION ---
            foreign_access = await client.get(
                f"/api/v1/dashboards/{dashboard_id}",
                headers=headers_other,
            )
            assert foreign_access.status_code in (403, 404)

            # --- J. EXPORT DASHBOARD ---
            export_res = await client.post(
                f"/api/v1/dashboards/{dashboard_id}/export",
                json={"format": "csv"},
                headers=headers_viewer,
            )
            assert export_res.status_code == 200
            assert "text/csv" in export_res.headers.get("content-type", "")

            # --- K. SOFT-DELETE (Archive) ---
            headers_owner = {
                "Authorization": f"Bearer {owner_token}",
                "X-Workspace-Id": str(ws.id),
            }
            del_res = await client.delete(
                f"/api/v1/dashboards/{dashboard_id}",
                headers=headers_owner,
            )
            assert del_res.status_code == 204

            # Verify excluded from normal list
            list_after = await client.get("/api/v1/dashboards", headers=headers_editor)
            assert not any(d["id"] == dashboard_id for d in list_after.json()["items"])

    finally:
        app.dependency_overrides.clear()
        await test_engine.dispose()


@pytest.mark.asyncio
async def test_widget_analytical_query_execution_and_cross_dataset_isolation():
    """
    Tests:
    1. Creation of physical Parquet dataset in Workspace A and Workspace B
    2. Cross-workspace dataset attachment rejection (Workspace A widget referencing Workspace B dataset)
    3. Analytical query execution for KPI card and Data Table widgets
    4. Runtime filter override verification
    """
    import json
    from pathlib import Path

    import pyarrow as pa
    import pyarrow.parquet as pq

    from app.models.dataset import Dataset
    from app.models.dataset_version import DatasetVersion

    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with session_maker() as session:
            user = User(
                full_name="Analytics Lead",
                email=f"lead_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            session.add(user)
            await session.flush()

            # Two workspaces
            ws_a = Workspace(name="Workspace A", owner_id=user.id)
            ws_b = Workspace(name="Workspace B", owner_id=user.id)
            session.add_all([ws_a, ws_b])
            await session.flush()

            m_a = WorkspaceMembership(workspace_id=ws_a.id, user_id=user.id, role="owner")
            m_b = WorkspaceMembership(workspace_id=ws_b.id, user_id=user.id, role="owner")
            session.add_all([m_a, m_b])
            await session.flush()

            # Create physical Parquet dataset in Workspace A
            storage_root = Path(settings.STORAGE_ROOT).resolve()
            storage_root.mkdir(parents=True, exist_ok=True)
            part_name_a = f"dash_part_{uuid.uuid4().hex[:8]}.parquet"
            part_path_a = storage_root / part_name_a

            records_a = {
                "category": ["Hardware", "Hardware", "Software", "Services"],
                "sales": [500.0, 750.0, 1200.0, 300.0],
                "region": ["North", "South", "North", "West"],
            }
            arrow_table_a = pa.Table.from_pydict(records_a)
            pq.write_table(arrow_table_a, part_path_a)

            manifest_a = {
                "dataset_name": "Sales Data A",
                "row_count": 4,
                "parts": [part_name_a],
                "columns": [
                    {"name": "category", "inferred_type": "string"},
                    {"name": "sales", "inferred_type": "numeric"},
                    {"name": "region", "inferred_type": "string"},
                ],
            }
            manifest_key_a = f"manifest_{uuid.uuid4().hex[:8]}.json"
            (storage_root / manifest_key_a).write_text(json.dumps(manifest_a), encoding="utf-8")

            dataset_a = Dataset(
                workspace_id=ws_a.id,
                name="Sales Data A",
                original_filename="sales_a.csv",
                file_type="csv",
                row_count=4,
                column_count=3,
            )
            session.add(dataset_a)
            await session.flush()

            version_a = DatasetVersion(
                dataset_id=dataset_a.id,
                version_number="v1",
                row_count=4,
                storage_key=manifest_key_a,
            )
            session.add(version_a)
            await session.flush()
            dataset_a.current_version_id = version_a.id

            # Create Dataset in Workspace B
            dataset_b = Dataset(
                workspace_id=ws_b.id,
                name="Secret Data B",
                original_filename="secret_b.csv",
                file_type="csv",
                row_count=10,
                column_count=2,
            )
            session.add(dataset_b)
            await session.commit()
            await session.refresh(dataset_a)
            await session.refresh(version_a)
            await session.refresh(dataset_b)

        token = create_access_token(user.id, user.email)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers_a = {
                "Authorization": f"Bearer {token}",
                "X-Workspace-Id": str(ws_a.id),
            }

            # 1. Create Dashboard in Workspace A
            dash_res = await client.post(
                "/api/v1/dashboards",
                json={"title": "Sales Analytics A"},
                headers=headers_a,
            )
            assert dash_res.status_code == 201
            dash_id = dash_res.json()["id"]

            # 2. Cross-workspace Dataset Attachment Rejection
            forbidden_widget = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets",
                json={
                    "widget_type": "bar",
                    "title": "Illegal Cross-Workspace Widget",
                    "dataset_id": str(dataset_b.id),  # Dataset from Workspace B!
                    "query_config": {"group_by_column": "category", "metric_column": "sales"},
                },
                headers=headers_a,
            )
            assert forbidden_widget.status_code in (400, 403, 404)

            # 3. Valid Widget Creation with Dataset A
            kpi_widget = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets",
                json={
                    "widget_type": "kpi",
                    "title": "Total Revenue",
                    "dataset_id": str(dataset_a.id),
                    "dataset_version_id": str(version_a.id),
                    "query_config": {"metric_column": "sales", "aggregation": "sum"},
                },
                headers=headers_a,
            )
            assert kpi_widget.status_code == 201
            kpi_widget_id = kpi_widget.json()["id"]

            # 4. Query KPI Widget without filters
            q_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets/{kpi_widget_id}/query",
                json={},
                headers=headers_a,
            )
            assert q_res.status_code == 200
            q_data = q_res.json()
            # 500 + 750 + 1200 + 300 = 2750.0
            assert q_data["data"]["value"] == 2750.0

            # 5. Query KPI Widget with Runtime Override Filter (region == North)
            # North sales: 500 + 1200 = 1700.0
            filter_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets/{kpi_widget_id}/query",
                json={
                    "filters": [
                        {"column": "region", "operator": "eq", "value": "North"}
                    ]
                },
                headers=headers_a,
            )
            assert filter_res.status_code == 200
            assert filter_res.json()["data"]["value"] == 1700.0

    finally:
        app.dependency_overrides.clear()
        await test_engine.dispose()
