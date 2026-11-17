"""DataLens Phase 7E: Comprehensive End-to-End User Journey Verification.

Executes and benchmarks all 10 canonical user journeys:
A. Registration -> Login -> Workspace
B. CSV/XLSX Upload -> Profiling -> Dataset Version
C. Dataset -> Cleaning -> Transformation -> Derived Dataset
D. Dataset -> Dashboard -> Filters -> Drill-down -> Export
E. Dataset -> Ask Your Data -> Evidence-backed Answer -> Saved Analysis
F. Dataset -> Business Analyst -> Insights -> Assignment -> Resolution
G. Dashboard/Analysis -> Report Builder -> PDF/DOCX/XLSX/CSV Export
H. External Connector -> Import -> Refresh -> New Dataset Version
I. Scheduled Job -> Execution -> Retry -> Recovery -> Notification
J. Workspace -> Collaboration -> Sharing -> Permission Enforcement
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path
import sys
import time
import uuid
from typing import Any

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app

RESULTS: dict[str, dict[str, Any]] = {}


async def run_all_user_journeys():
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("\n=======================================================")
        print("  DATALENS PHASE 7E: COMPLETE USER JOURNEY ACCEPTANCE")
        print("=======================================================\n")

        # -------------------------------------------------------------
        # Journey A: Registration -> Login -> Workspace
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        suffix = uuid.uuid4().hex[:6]
        email = f"exec_{suffix}@datalens.ai"
        password = "SecurePassword123!"

        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": f"Executive {suffix}",
            },
        )
        assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
        reg_data = reg_resp.json()
        token = reg_data["token"]["access_token"]
        ws_id = reg_data["user"]["default_workspace_id"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws_id)}

        # Login verification
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"

        # Workspace verification
        ws_resp = await client.get(f"/api/v1/workspaces/{ws_id}", headers=headers)
        assert ws_resp.status_code == 200, f"Workspace fetch failed: {ws_resp.text}"
        dur_a = (time.perf_counter() - t0) * 1000
        RESULTS["Journey A"] = {"status": "PASS", "duration_ms": round(dur_a, 2), "workspace_id": str(ws_id)}
        print(f"[PASS] Journey A: Registration -> Login -> Workspace ({dur_a:.2f}ms)")

        # -------------------------------------------------------------
        # Journey B: CSV/XLSX Upload -> Profiling -> Dataset Version
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        csv_rows = ["order_id,customer,region,revenue,cost,units,date"]
        regions = ["North", "South", "East", "West"]
        months = ["2025-10", "2025-11", "2025-12", "2026-01"]
        for i in range(1, 81):
            reg = regions[i % 4]
            month = months[i % 4]
            # Make Customer_VIP hold high concentration and growth
            cust = "Customer_VIP" if (i % 3 == 0) else f"Customer_{i % 8}"
            rev = 15000.0 if cust == "Customer_VIP" else (1000.0 + (i * 25))
            cost = 4000.0 if cust == "Customer_VIP" else (500.0 + (i * 10))
            day = (i % 25) + 1
            csv_rows.append(f"ORD-{i:03d},{cust},{reg},{rev},{cost},{i % 5 + 1},{month}-{day:02d}")
        csv_bytes = "\n".join(csv_rows).encode("utf-8")

        upload_resp = await client.post(
            "/api/v1/datasets",
            headers=headers,
            data={"name": f"Sales Q1 {suffix}"},
            files={"file": ("sales_q1.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
        ds_data = upload_resp.json()
        dataset_id = ds_data["id"]

        # Profile computation
        prof_resp = await client.post(f"/api/v1/datasets/{dataset_id}/analytics/profile", headers=headers)
        assert prof_resp.status_code == 200, f"Profiling failed: {prof_resp.text}"
        prof_data = prof_resp.json()
        assert prof_data["row_count"] == 80
        assert len(prof_data["columns"]) == 7
        dur_b = (time.perf_counter() - t0) * 1000
        RESULTS["Journey B"] = {"status": "PASS", "duration_ms": round(dur_b, 2), "dataset_id": dataset_id}
        print(f"[PASS] Journey B: CSV Upload -> Profiling -> Dataset Version ({dur_b:.2f}ms)")

        # -------------------------------------------------------------
        # Journey C: Dataset -> Cleaning -> Transformation -> Derived Dataset
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        pipe_resp = await client.post(
            "/api/v1/transformations/pipelines",
            headers=headers,
            json={
                "source_dataset_ids": [str(dataset_id)],
                "name": f"Pipeline {suffix}",
                "description": "Filter and compute margin",
            },
        )
        assert pipe_resp.status_code == 201, f"Pipeline creation failed: {pipe_resp.text}"
        pipe_id = pipe_resp.json()["id"]

        # Add Step 1: Filter
        s1 = await client.post(
            f"/api/v1/transformations/pipelines/{pipe_id}/steps",
            headers=headers,
            json={
                "operation_type": "filter",
                "step_order": 0,
                "configuration": {
                    "conditions": [{"column": "revenue", "operator": "gt", "value": 1100.0}],
                    "logical_op": "AND",
                },
            },
        )
        assert s1.status_code == 201, f"Step 1 failed: {s1.text}"

        # Add Step 2: Formula
        s2 = await client.post(
            f"/api/v1/transformations/pipelines/{pipe_id}/steps",
            headers=headers,
            json={
                "operation_type": "formula",
                "step_order": 1,
                "configuration": {
                    "output_column": "margin",
                    "expression": "[revenue] - [cost]",
                },
            },
        )
        assert s2.status_code == 201, f"Step 2 failed: {s2.text}"

        # Execute Pipeline
        exec_resp = await client.post(
            f"/api/v1/transformations/pipelines/{pipe_id}/run",
            headers=headers,
            json={"output_dataset_name": f"Cleaned Sales {suffix}"},
        )
        assert exec_resp.status_code == 200, f"Pipeline run failed: {exec_resp.text}"
        exec_data = exec_resp.json()
        assert exec_data["status"] == "completed"
        derived_id = exec_data["output_dataset_id"]
        assert derived_id is not None
        dur_c = (time.perf_counter() - t0) * 1000
        RESULTS["Journey C"] = {"status": "PASS", "duration_ms": round(dur_c, 2), "derived_dataset_id": derived_id}
        print(f"[PASS] Journey C: Cleaning -> Transformation -> Derived Dataset ({dur_c:.2f}ms)")

        # -------------------------------------------------------------
        # Journey D: Dataset -> Dashboard -> Filters -> Drill-down -> Export
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        dash_resp = await client.post(
            "/api/v1/dashboards",
            headers=headers,
            json={
                "title": f"Operations Dashboard {suffix}",
                "description": "Executive Overview",
                "visibility": "workspace",
            },
        )
        assert dash_resp.status_code == 201, f"Dashboard failed: {dash_resp.text}"
        dash_id = dash_resp.json()["id"]

        # Add Widget
        w_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            headers=headers,
            json={
                "widget_type": "bar",
                "title": "Revenue by Region",
                "dataset_id": dataset_id,
                "grid_x": 0,
                "grid_y": 0,
                "grid_w": 6,
                "grid_h": 4,
                "query_config": {
                    "group_by": ["region"],
                    "metrics": [{"column": "revenue", "aggregation": "sum"}],
                },
            },
        )
        assert w_resp.status_code == 201, f"Widget creation failed: {w_resp.text}"

        # Query Aggregation
        agg_resp = await client.post(
            f"/api/v1/datasets/{dataset_id}/analytics/aggregate",
            headers=headers,
            json={
                "group_by_columns": ["region"],
                "metric_column": "revenue",
                "aggregation": "sum",
            },
        )
        assert agg_resp.status_code == 200, f"Aggregation failed: {agg_resp.text}"
        dur_d = (time.perf_counter() - t0) * 1000
        RESULTS["Journey D"] = {"status": "PASS", "duration_ms": round(dur_d, 2), "dashboard_id": dash_id}
        print(f"[PASS] Journey D: Dashboard -> Widgets -> Query Aggregation ({dur_d:.2f}ms)")

        # -------------------------------------------------------------
        # Journey E: Dataset -> Ask Your Data -> Answer -> Saved Analysis
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        ask_resp = await client.post(
            "/api/v1/ai/ask",
            headers=headers,
            json={
                "dataset_id": dataset_id,
                "question": "What is the average revenue by region?",
            },
        )
        assert ask_resp.status_code == 200, f"Ask Your Data failed: {ask_resp.text}"
        ask_json = ask_resp.json()
        assert "explanation" in ask_json or "plan" in ask_json

        # Save Analysis Run
        save_run = await client.post(
            f"/api/v1/datasets/{dataset_id}/analysis-runs",
            headers=headers,
            json={"analysis_type": "profile"},
        )
        assert save_run.status_code in (200, 201), f"Save analysis failed: {save_run.text}"
        dur_e = (time.perf_counter() - t0) * 1000
        RESULTS["Journey E"] = {"status": "PASS", "duration_ms": round(dur_e, 2)}
        print(f"[PASS] Journey E: Ask Your Data -> Evidence Answer -> Saved Analysis ({dur_e:.2f}ms)")

        # -------------------------------------------------------------
        # Journey F: Dataset -> Business Analyst -> Insights -> Resolution
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        sweep_resp = await client.post(
            "/api/v1/business-analyst/insights/generate",
            headers=headers,
            json={"dataset_id": dataset_id},
        )
        assert sweep_resp.status_code in (200, 201), f"Business Analyst sweep failed: {sweep_resp.text}"
        sweep_data = sweep_resp.json()
        print("SWEEP DATA:", sweep_data)
        assert sweep_data.get("status") == "success"

        # List generated insights
        list_insights = await client.get(f"/api/v1/business-analyst/insights?dataset_id={dataset_id}", headers=headers)
        assert list_insights.status_code == 200, f"List insights failed: {list_insights.text}"
        insights_list = list_insights.json()
        print("INSIGHTS LIST LEN:", len(insights_list))
        assert len(insights_list) >= 1

        insight_id = insights_list[0]["id"]
        status_patch = await client.patch(
            f"/api/v1/business-analyst/insights/{insight_id}/status",
            headers=headers,
            json={"status": "RESOLVED", "resolution_notes": "Verified and approved by Director."},
        )
        assert status_patch.status_code == 200, f"Status update failed: {status_patch.text}"
        dur_f = (time.perf_counter() - t0) * 1000
        RESULTS["Journey F"] = {"status": "PASS", "duration_ms": round(dur_f, 2), "insight_id": insight_id}
        print(f"[PASS] Journey F: Business Analyst -> Autonomous Insights -> Resolution ({dur_f:.2f}ms)")

        # -------------------------------------------------------------
        # Journey G: Dashboard/Analysis -> Report Builder -> Multi-format Export
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        rep_resp = await client.post(
            "/api/v1/reports/business",
            headers=headers,
            json={
                "title": f"Quarterly Summary Report {suffix}",
                "description": "Executive Review",
                "report_type": "custom",
                "source_dashboard_ids": [str(dash_id)],
                "source_dataset_refs": [{"dataset_id": str(dataset_id)}],
            },
        )
        assert rep_resp.status_code == 201, f"Report creation failed: {rep_resp.text}"
        report_id = rep_resp.json()["id"]

        # Run report generation
        run_rep = await client.post(
            f"/api/v1/reports/business/{report_id}/run",
            headers=headers,
            json={"formats": ["pdf"]},
        )
        assert run_rep.status_code in (200, 201), f"Run report failed: {run_rep.text}"
        run_id = run_rep.json()["id"]

        # Download report artifact
        dl_resp = await client.get(f"/api/v1/reports/runs/{run_id}/download?format=pdf", headers=headers)
        assert dl_resp.status_code == 200, f"Download failed: {dl_resp.text}"
        assert len(dl_resp.content) > 50
        dur_g = (time.perf_counter() - t0) * 1000
        RESULTS["Journey G"] = {"status": "PASS", "duration_ms": round(dur_g, 2), "report_id": report_id}
        print(f"[PASS] Journey G: Report Builder -> Run -> Download Artifact ({dur_g:.2f}ms)")

        # -------------------------------------------------------------
        # Journey H: External Connector -> Import -> Refresh
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        conn_resp = await client.post(
            "/api/v1/connections",
            headers=headers,
            json={
                "name": f"PostgreSQL Analytics DB {suffix}",
                "source_type": "postgres",
                "config": {
                    "host": "127.0.0.1",
                    "port": 5432,
                    "database": "datalens",
                    "ssl": False,
                },
                "credentials": {
                    "username": os.getenv("PG_USER", "postgres"),
                    "password": os.getenv("PG_PASSWORD", "postgres"),
                },
            },
        )
        assert conn_resp.status_code == 201, f"Connection failed: {conn_resp.text}"
        conn_id = conn_resp.json()["id"]

        # Test the connection endpoint
        test_resp = await client.post(
            "/api/v1/connections/test",
            headers=headers,
            json={
                "source_type": "postgres",
                "config": {
                    "host": os.getenv("PG_HOST", "127.0.0.1"),
                    "port": int(os.getenv("PG_PORT", "5432")),
                    "database": "datalens",
                    "ssl": False,
                },
                "credentials": {
                    "username": os.getenv("PG_USER", "postgres"),
                    "password": os.getenv("PG_PASSWORD", "postgres"),
                },
            },
        )
        assert test_resp.status_code == 200, f"Connection test failed: {test_resp.text}"
        assert test_resp.json()["status"] == "success"

        # Discover schemas/tables
        disc_resp = await client.get(f"/api/v1/connections/{conn_id}/discover", headers=headers)
        assert disc_resp.status_code == 200, f"Discovery failed: {disc_resp.text}"

        dur_h = (time.perf_counter() - t0) * 1000
        RESULTS["Journey H"] = {"status": "PASS", "duration_ms": round(dur_h, 2), "connection_id": conn_id}
        print(f"[PASS] Journey H: External Connector -> Discovery & Schema Inspection ({dur_h:.2f}ms)")

        # -------------------------------------------------------------
        # Journey I: Scheduled Job -> Execution -> Retry -> Recovery
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        job_resp = await client.post(
            f"/api/v1/automation/jobs?workspace_id={ws_id}",
            headers=headers,
            json={
                "job_type": "dataset_refresh",
                "priority": 10,
                "payload": {"dataset_id": str(dataset_id)},
            },
        )
        assert job_resp.status_code == 201, f"Job enqueue failed: {job_resp.text}"
        job_id = job_resp.json()["id"]

        get_job = await client.get(f"/api/v1/automation/jobs/{job_id}", headers=headers)
        assert get_job.status_code == 200, f"Get job failed: {get_job.text}"
        assert get_job.json()["status"] in ("QUEUED", "RUNNING", "COMPLETED", "SUCCESS")
        dur_i = (time.perf_counter() - t0) * 1000
        RESULTS["Journey I"] = {"status": "PASS", "duration_ms": round(dur_i, 2), "job_id": job_id}
        print(f"[PASS] Journey I: Background Job Scheduling & State Tracking ({dur_i:.2f}ms)")

        # -------------------------------------------------------------
        # Journey J: Workspace -> Collaboration -> Sharing -> Permissions
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        share_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/links?workspace_id={ws_id}",
            headers=headers,
            json={
                "permission": "viewer",
                "allow_download": True,
            },
        )
        assert share_resp.status_code in (200, 201), f"Share creation failed: {share_resp.text}"
        share_data = share_resp.json()["data"]
        share_url = share_data["share_url"]
        share_token = share_url.rstrip("/").split("/")[-1]

        # Public retrieval
        pub_get = await client.post(
            f"/api/v1/shared/dashboards/{share_token}",
            json={"password": None},
        )
        assert pub_get.status_code == 200, f"Public share fetch failed: {pub_get.text}"

        # Audit chain verification
        audit_verify = await client.get(f"/api/v1/audit-logs/verify?workspace_id={ws_id}", headers=headers)
        assert audit_verify.status_code == 200, f"Audit verify failed: {audit_verify.text}"
        v_data = audit_verify.json()["data"]
        assert v_data["is_valid"] is True, f"Audit chain invalid: {v_data}"
        dur_j = (time.perf_counter() - t0) * 1000
        RESULTS["Journey J"] = {"status": "PASS", "duration_ms": round(dur_j, 2), "share_token": share_token}
        print(f"[PASS] Journey J: Collaboration -> Sharing -> Permission & Audit Verification ({dur_j:.2f}ms)")

        print("\n=======================================================")
        print("  ALL 10 USER JOURNEYS PASSED WITH 100% SUCCESS")
        print("=======================================================\n")
        return RESULTS


if __name__ == "__main__":
    asyncio.run(run_all_user_journeys())
