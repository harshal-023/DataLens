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
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.transformation.formula_engine import FormulaEngine, FormulaError

# ---------------------------------------------------------------------------
# Unit Tests for Formula Engine
# ---------------------------------------------------------------------------

def test_formula_engine_basic_arithmetic():
    expr = "[price] * [quantity] * (1 - [discount])"
    ast, sql, cols = FormulaEngine.parse_and_validate(expr, ["price", "quantity", "discount"])
    assert cols == ["discount", "price", "quantity"]
    assert '"price"' in sql
    assert '"quantity"' in sql
    assert '"discount"' in sql
    assert "*" in sql


def test_formula_engine_safe_division():
    expr = "[sales] / [units]"
    ast, sql, cols = FormulaEngine.parse_and_validate(expr, ["sales", "units"])
    assert 'NULLIF("units", 0)' in sql


def test_formula_engine_functions():
    expr = "IF([revenue] > 1000, UPPER([category]), 'LOW')"
    ast, sql, cols = FormulaEngine.parse_and_validate(expr, ["revenue", "category"])
    assert "CASE WHEN" in sql
    assert "UPPER(" in sql
    assert "'LOW'" in sql


def test_formula_engine_invalid_column():
    expr = "[sales] + [nonexistent_col]"
    with pytest.raises(FormulaError, match="Unknown column"):
        FormulaEngine.parse_and_validate(expr, ["sales"])


def test_formula_engine_unknown_function():
    expr = "HACK([sales])"
    with pytest.raises(FormulaError, match="Unsupported function"):
        FormulaEngine.parse_and_validate(expr, ["sales"])


# ---------------------------------------------------------------------------
# Integration Tests: Pipelines, Steps, Joins, Execution, RBAC & Isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transformations_end_to_end(tmp_path):
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
                full_name="Prep Owner",
                email=f"prep_owner_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            editor = User(
                full_name="Prep Editor",
                email=f"prep_editor_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            viewer = User(
                full_name="Prep Viewer",
                email=f"prep_viewer_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            other_user = User(
                full_name="Other User",
                email=f"prep_other_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            session.add_all([owner, editor, viewer, other_user])
            await session.commit()
            await session.refresh(owner)
            await session.refresh(editor)
            await session.refresh(viewer)
            await session.refresh(other_user)

            # 2. Setup Workspaces
            ws = Workspace(name=f"Data Prep Workspace {uuid.uuid4().hex[:6]}", owner_id=owner.id)
            ws_other = Workspace(name="Foreign Workspace", owner_id=other_user.id)
            session.add_all([ws, ws_other])
            await session.commit()
            await session.refresh(ws)
            await session.refresh(ws_other)

            session.add_all([
                WorkspaceMembership(workspace_id=ws.id, user_id=owner.id, role="owner"),
                WorkspaceMembership(workspace_id=ws.id, user_id=editor.id, role="editor"),
                WorkspaceMembership(workspace_id=ws.id, user_id=viewer.id, role="viewer"),
                WorkspaceMembership(workspace_id=ws_other.id, user_id=other_user.id, role="owner"),
            ])
            await session.commit()

            # 3. Create 2 test datasets with real Parquet files
            storage_root = Path(settings.STORAGE_ROOT).resolve()

            # Dataset A: Orders (order_id, customer_id, product, price, quantity)
            ds_orders_id = uuid.uuid4()
            ver_orders_id = uuid.uuid4()
            rel_orders_dir = f"datasets/{ws.id}/{ds_orders_id}/{ver_orders_id}/processed"
            (storage_root / rel_orders_dir).mkdir(parents=True, exist_ok=True)

            orders_parquet = storage_root / rel_orders_dir / "part_0.parquet"
            orders_table = pa.Table.from_pydict({
                "order_id": [101, 102, 103, 104],
                "customer_id": [1, 2, 1, 3],
                "product": ["Widget", "Gadget", "Widget", "Gizmo"],
                "price": [10.0, 25.0, 10.0, 50.0],
                "quantity": [2, 1, 4, None],
            })
            pq.write_table(orders_table, orders_parquet)

            orders_manifest = {
                "parts": [f"{rel_orders_dir}/part_0.parquet"],
                "row_count": 4,
                "column_count": 5,
                "columns": [
                    {"name": "order_id", "inferred_type": "integer"},
                    {"name": "customer_id", "inferred_type": "integer"},
                    {"name": "product", "inferred_type": "string"},
                    {"name": "price", "inferred_type": "float"},
                    {"name": "quantity", "inferred_type": "integer"},
                ],
            }
            orders_manifest_path = storage_root / rel_orders_dir / "manifest.json"
            orders_manifest_path.write_text(json.dumps(orders_manifest), encoding="utf-8")

            ds_orders = Dataset(
                id=ds_orders_id,
                workspace_id=ws.id,
                uploaded_by=owner.id,
                name="Orders Dataset",
                original_filename="orders.parquet",
                file_type="parquet",
                row_count=4,
                column_count=5,
                status="ready",
                is_archived=False,
            )
            session.add(ds_orders)
            await session.flush()

            ver_orders = DatasetVersion(
                id=ver_orders_id,
                dataset_id=ds_orders_id,
                version_number="v1",
                storage_key=f"{rel_orders_dir}/manifest.json",
                original_storage_key=f"{rel_orders_dir}/manifest.json",
                file_size=orders_parquet.stat().st_size,
                schema_metadata={"columns": orders_manifest["columns"]},
                row_count=4,
                column_count=5,
                status="ready",
            )
            session.add(ver_orders)
            await session.flush()
            ds_orders.current_version_id = ver_orders.id

            # Dataset B: Customers (cust_id, customer_name, country)
            ds_cust_id = uuid.uuid4()
            ver_cust_id = uuid.uuid4()
            rel_cust_dir = f"datasets/{ws.id}/{ds_cust_id}/{ver_cust_id}/processed"
            (storage_root / rel_cust_dir).mkdir(parents=True, exist_ok=True)

            cust_parquet = storage_root / rel_cust_dir / "part_0.parquet"
            cust_table = pa.Table.from_pydict({
                "cust_id": [1, 2, 4],
                "customer_name": ["Alice Corp", "Bob LLC", "Dave Inc"],
                "country": ["USA", "Canada", "UK"],
            })
            pq.write_table(cust_table, cust_parquet)

            cust_manifest = {
                "parts": [f"{rel_cust_dir}/part_0.parquet"],
                "row_count": 3,
                "column_count": 3,
                "columns": [
                    {"name": "cust_id", "inferred_type": "integer"},
                    {"name": "customer_name", "inferred_type": "string"},
                    {"name": "country", "inferred_type": "string"},
                ],
            }
            (storage_root / rel_cust_dir / "manifest.json").write_text(json.dumps(cust_manifest), encoding="utf-8")

            ds_cust = Dataset(
                id=ds_cust_id,
                workspace_id=ws.id,
                uploaded_by=owner.id,
                name="Customers Dataset",
                original_filename="customers.parquet",
                file_type="parquet",
                row_count=3,
                column_count=3,
                status="ready",
                is_archived=False,
            )
            session.add(ds_cust)
            await session.flush()

            ver_cust = DatasetVersion(
                id=ver_cust_id,
                dataset_id=ds_cust_id,
                version_number="v1",
                storage_key=f"{rel_cust_dir}/manifest.json",
                original_storage_key=f"{rel_cust_dir}/manifest.json",
                file_size=cust_parquet.stat().st_size,
                schema_metadata={"columns": cust_manifest["columns"]},
                row_count=3,
                column_count=3,
                status="ready",
            )
            session.add(ver_cust)
            await session.flush()
            ds_cust.current_version_id = ver_cust.id

            await session.commit()

        editor_token = create_access_token(editor.id, editor.email)
        viewer_token = create_access_token(viewer.id, viewer.email)
        other_token = create_access_token(other_user.id, other_user.email)

        headers_editor = {"Authorization": f"Bearer {editor_token}", "X-Workspace-Id": str(ws.id)}
        headers_viewer = {"Authorization": f"Bearer {viewer_token}", "X-Workspace-Id": str(ws.id)}
        headers_other = {"Authorization": f"Bearer {other_token}", "X-Workspace-Id": str(ws_other.id)}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Validate Formula Dry-Run Endpoint
            val_res = await ac.post(
                "/api/v1/transformations/validate-formula",
                headers=headers_viewer,
                json={
                    "expression": "IF([price] > 20, [price] * 0.9, [price])",
                    "columns": [{"name": "price", "data_type": "float"}],
                },
            )
            assert val_res.status_code == 200
            val_data = val_res.json()
            assert val_data["valid"] is True
            assert val_data["referenced_columns"] == ["price"]

            # 2. Pipeline CRUD
            create_pipe_res = await ac.post(
                "/api/v1/transformations/pipelines",
                headers=headers_editor,
                json={
                    "name": "Customer Orders Enrichment",
                    "description": "Joins orders with customers and cleans nulls",
                    "source_dataset_ids": [str(ds_orders_id), str(ds_cust_id)],
                },
            )
            assert create_pipe_res.status_code == 201
            pipe = create_pipe_res.json()
            pipeline_id = pipe["id"]
            assert pipe["name"] == "Customer Orders Enrichment"

            # List pipelines
            list_res = await ac.post(
                "/api/v1/transformations/pipelines",
                headers=headers_viewer,
                json={"name": "Viewer Try", "source_dataset_ids": []},
            )
            assert list_res.status_code == 403  # Viewer cannot create pipeline

            get_pipe_res = await ac.get(f"/api/v1/transformations/pipelines/{pipeline_id}", headers=headers_viewer)
            assert get_pipe_res.status_code == 200

            # 3. Add Steps
            # Step 1: Clean nulls in quantity (fill with 1)
            step1_res = await ac.post(
                f"/api/v1/transformations/pipelines/{pipeline_id}/steps",
                headers=headers_editor,
                json={
                    "operation_type": "clean_nulls",
                    "step_order": 0,
                    "configuration": {
                        "strategies": [{"column": "quantity", "strategy": "fill_value", "fill_value": 1}]
                    },
                },
            )
            assert step1_res.status_code == 201

            # Step 2: Inner Join with Customers
            step2_res = await ac.post(
                f"/api/v1/transformations/pipelines/{pipeline_id}/steps",
                headers=headers_editor,
                json={
                    "operation_type": "join",
                    "step_order": 1,
                    "configuration": {
                        "right_dataset_id": str(ds_cust_id),
                        "join_type": "inner",
                        "join_keys": [{"left": "customer_id", "right": "cust_id"}],
                    },
                },
            )
            assert step2_res.status_code == 201

            # Step 3: Formula (total_amount = price * quantity)
            step3_res = await ac.post(
                f"/api/v1/transformations/pipelines/{pipeline_id}/steps",
                headers=headers_editor,
                json={
                    "operation_type": "formula",
                    "step_order": 2,
                    "configuration": {
                        "output_column": "total_amount",
                        "expression": "[price] * [quantity]",
                    },
                },
            )
            assert step3_res.status_code == 201

            # 4. Preview Pipeline
            prev_res = await ac.post(
                f"/api/v1/transformations/pipelines/{pipeline_id}/preview",
                headers=headers_viewer,
                json={"limit": 10},
            )
            assert prev_res.status_code == 200
            prev_data = prev_res.json()
            assert prev_data["step_executed"] == 3
            # Customer 1 has 2 orders, Customer 2 has 1 order -> total 3 rows
            assert len(prev_data["rows"]) == 3
            col_names = [c["name"] for c in prev_data["columns"]]
            assert "total_amount" in col_names
            assert "customer_name" in col_names

            # 5. Execute Run Pipeline
            run_res = await ac.post(
                f"/api/v1/transformations/pipelines/{pipeline_id}/run",
                headers=headers_editor,
                json={"output_dataset_name": "Enriched Orders Master"},
            )
            assert run_res.status_code == 200
            run_data = run_res.json()
            assert run_data["status"] == "completed"
            assert run_data["row_count"] == 3
            assert run_data["output_dataset_id"] is not None
            assert run_data["execution_duration_ms"] >= 0

            # 6. Verify Created Derived Dataset exists in workspace
            derived_id = run_data["output_dataset_id"]
            derived_res = await ac.get(f"/api/v1/datasets/{derived_id}", headers=headers_viewer)
            assert derived_res.status_code == 200
            derived_data = derived_res.json()
            assert derived_data["name"] == "Enriched Orders Master"
            assert derived_data["row_count"] == 3

            # 7. Cross-Workspace Isolation
            iso_res = await ac.get(f"/api/v1/transformations/pipelines/{pipeline_id}", headers=headers_other)
            assert iso_res.status_code == 404

    finally:
        app.dependency_overrides.clear()
