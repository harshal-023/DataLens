"""
DataLens - Phase 4 Comprehensive Final Integration Audit & E2E Verification
Validates the complete unified pipeline across:
- Phase 4A: Interactive Dashboard Builder & Multi-chart Widget System
- Phase 4B: Advanced Data Transformation & Data Preparation Engine
- Phase 4C: Advanced Interactive Visualization & Cross-filtering Engine
- Phase 4D: Automated Business Reporting, Multi-format Export & Scheduling Engine
"""

import io
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import openpyxl
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.business_report import ReportSchedule
from app.models.dataset_version import DatasetVersion
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.email_adapter import dev_email_adapter
from app.services.reports.email_delivery import EmailDeliveryService
from app.services.reports.scheduler_service import ReportSchedulerService

# Global performance metrics dictionary recorded during live execution
AUDIT_BENCHMARKS: dict[str, Any] = {}


@pytest.mark.asyncio
async def test_phase4_full_integration_workflow_and_audit():
    """
    Executes the comprehensive 17-step end-to-end integration workflow
    validating data integrity, security RBAC, DuckDB query engine, and multi-format reporting.
    """
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with session_maker() as session:
            # =====================================================================
            # SETUP USERS AND WORKSPACES
            # =====================================================================
            suffix = uuid.uuid4().hex[:6]
            owner = User(
                full_name=f"Audit Owner {suffix}",
                email=f"audit_owner_{suffix}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            editor = User(
                full_name=f"Audit Editor {suffix}",
                email=f"audit_editor_{suffix}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            viewer = User(
                full_name=f"Audit Viewer {suffix}",
                email=f"audit_viewer_{suffix}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            foreign_user = User(
                full_name=f"Foreign User {suffix}",
                email=f"foreign_user_{suffix}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            session.add_all([owner, editor, viewer, foreign_user])
            await session.commit()
            await session.refresh(owner)
            await session.refresh(editor)
            await session.refresh(viewer)
            await session.refresh(foreign_user)

            # Primary Workspace (ws_alpha) and Foreign Workspace (ws_beta)
            ws_alpha = Workspace(name=f"Audit Primary WS {suffix}", owner_id=owner.id)
            ws_beta = Workspace(name=f"Audit Foreign WS {suffix}", owner_id=foreign_user.id)
            session.add_all([ws_alpha, ws_beta])
            await session.commit()
            await session.refresh(ws_alpha)
            await session.refresh(ws_beta)

            session.add_all([
                WorkspaceMembership(workspace_id=ws_alpha.id, user_id=owner.id, role="owner"),
                WorkspaceMembership(workspace_id=ws_alpha.id, user_id=editor.id, role="editor"),
                WorkspaceMembership(workspace_id=ws_alpha.id, user_id=viewer.id, role="viewer"),
                WorkspaceMembership(workspace_id=ws_beta.id, user_id=foreign_user.id, role="owner"),
            ])
            await session.commit()

        owner_token = create_access_token(user_id=owner.id, email=owner.email)
        editor_token = create_access_token(user_id=editor.id, email=editor.email)
        viewer_token = create_access_token(user_id=viewer.id, email=viewer.email)
        foreign_token = create_access_token(user_id=foreign_user.id, email=foreign_user.email)

        headers_owner = {"Authorization": f"Bearer {owner_token}", "X-Workspace-ID": str(ws_alpha.id)}
        headers_editor = {"Authorization": f"Bearer {editor_token}", "X-Workspace-ID": str(ws_alpha.id)}
        headers_viewer = {"Authorization": f"Bearer {viewer_token}", "X-Workspace-ID": str(ws_alpha.id)}
        headers_foreign = {"Authorization": f"Bearer {foreign_token}", "X-Workspace-ID": str(ws_beta.id)}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # =====================================================================
            # 1. UPLOAD CSV AND EXCEL DATASETS
            # =====================================================================
            t0_csv = time.perf_counter()
            csv_rows = [
                "transaction_id,customer_id,product_category,region,order_date,amount,units,discount"
            ]
            categories = ["Electronics", "Software", "Cloud Services", "Hardware"]
            regions = ["North America", "EMEA", "APAC", "LATAM"]
            for i in range(1, 101):
                cat = categories[i % len(categories)]
                reg = regions[i % len(regions)]
                cust = f"CUST_{(i % 25) + 1:03d}"
                amt = 100.0 + (i * 15.5)
                units = (i % 5) + 1
                disc = 0.05 if i % 2 == 0 else 0.10
                date = f"2026-0{(i % 6) + 1:01d}-{(i % 28) + 1:02d}"
                csv_rows.append(f"TX_{i:04d},{cust},{cat},{reg},{date},{amt:.2f},{units},{disc:.2f}")

            csv_content = "\n".join(csv_rows).encode("utf-8")
            res_csv = await client.post(
                "/api/v1/datasets",
                data={"name": "Transactions CSV"},
                files={"file": ("transactions.csv", csv_content, "text/csv")},
                headers=headers_owner,
            )
            t1_csv = time.perf_counter()
            AUDIT_BENCHMARKS["upload_csv_duration_ms"] = round((t1_csv - t0_csv) * 1000, 2)
            assert res_csv.status_code == 201, res_csv.text
            ds_orders = res_csv.json()
            orders_id = ds_orders["id"]

            # Excel dataset (Customers)
            t0_xlsx = time.perf_counter()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Customers"
            ws.append(["customer_id", "customer_name", "customer_tier", "country"])
            tiers = ["Enterprise", "Mid-Market", "SMB"]
            countries = ["United States", "Germany", "United Kingdom", "Japan", "Brazil"]
            for j in range(1, 26):
                c_id = f"CUST_{j:03d}"
                c_name = f"Global Partner {j}"
                c_tier = tiers[j % len(tiers)]
                c_country = countries[j % len(countries)]
                ws.append([c_id, c_name, c_tier, c_country])

            xlsx_buffer = io.BytesIO()
            wb.save(xlsx_buffer)
            xlsx_content = xlsx_buffer.getvalue()

            res_xlsx = await client.post(
                "/api/v1/datasets",
                data={"name": "Customers XLSX", "selected_worksheet": "Customers"},
                files={
                    "file": (
                        "customers.xlsx",
                        xlsx_content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                headers=headers_editor,
            )
            t1_xlsx = time.perf_counter()
            AUDIT_BENCHMARKS["upload_xlsx_duration_ms"] = round((t1_xlsx - t0_xlsx) * 1000, 2)
            assert res_xlsx.status_code == 201, res_xlsx.text
            ds_customers = res_xlsx.json()
            customers_id = ds_customers["id"]

            # =====================================================================
            # 2. VERIFY PROFILING & IMMUTABLE VERSION CREATION
            # =====================================================================
            res_orders_detail = await client.get(f"/api/v1/datasets/{orders_id}", headers=headers_editor)
            assert res_orders_detail.status_code == 200
            orders_detail = res_orders_detail.json()
            assert orders_detail["status"] == "ready"
            assert orders_detail["row_count"] == 100
            assert orders_detail["column_count"] == 8

            res_cust_detail = await client.get(f"/api/v1/datasets/{customers_id}", headers=headers_editor)
            assert res_cust_detail.status_code == 200
            cust_detail = res_cust_detail.json()
            assert cust_detail["status"] == "ready"
            assert cust_detail["row_count"] == 25
            assert cust_detail["column_count"] == 4

            # Verify initial version manifests
            async with session_maker() as s:
                v_orders_init = (
                    await s.execute(
                        DatasetVersion.__table__.select().where(DatasetVersion.dataset_id == uuid.UUID(orders_id))
                    )
                ).first()
                v_cust_init = (
                    await s.execute(
                        DatasetVersion.__table__.select().where(DatasetVersion.dataset_id == uuid.UUID(customers_id))
                    )
                ).first()
                initial_orders_sha = v_orders_init.checksum
                initial_cust_sha = v_cust_init.checksum
                assert len(initial_orders_sha) == 64
                assert len(initial_cust_sha) == 64

            # =====================================================================
            # 3, 4, 5. TRANSFORMATION PIPELINE, JOIN, CLEAN, FORMULA
            # =====================================================================
            pipeline_payload = {
                "name": "Enriched Global Sales Pipeline",
                "description": "Joins orders with customers, filters high values, and calculates net revenue",
                "source_dataset_ids": [str(orders_id), str(customers_id)],
            }
            res_pipe = await client.post(
                "/api/v1/transformations/pipelines", json=pipeline_payload, headers=headers_editor
            )
            assert res_pipe.status_code == 201, res_pipe.text
            pipe_id = res_pipe.json()["id"]

            # Step 1: Join with Customers on customer_id
            step1_payload = {
                "operation_type": "join",
                "step_order": 0,
                "configuration": {
                    "right_dataset_id": str(customers_id),
                    "join_type": "inner",
                    "join_keys": [{"left": "customer_id", "right": "customer_id"}],
                },
            }
            res_s1 = await client.post(
                f"/api/v1/transformations/pipelines/{pipe_id}/steps", json=step1_payload, headers=headers_editor
            )
            assert res_s1.status_code == 201, res_s1.text

            # Step 2: Filter amount > 150.0
            step2_payload = {
                "operation_type": "filter",
                "step_order": 1,
                "configuration": {
                    "conditions": [{"column": "amount", "operator": "gt", "value": 150.0}],
                    "logical_op": "AND",
                },
            }
            res_s2 = await client.post(
                f"/api/v1/transformations/pipelines/{pipe_id}/steps", json=step2_payload, headers=headers_editor
            )
            assert res_s2.status_code == 201, res_s2.text

            # Step 3: Formula calculated column
            step3_payload = {
                "operation_type": "formula",
                "step_order": 2,
                "configuration": {
                    "output_column": "net_revenue",
                    "expression": "[amount] * (1 - [discount])",
                },
            }
            res_s3 = await client.post(
                f"/api/v1/transformations/pipelines/{pipe_id}/steps", json=step3_payload, headers=headers_editor
            )
            assert res_s3.status_code == 201, res_s3.text

            # =====================================================================
            # 6. EXECUTE PIPELINE & MATERIALIZE DERIVED PARQUET DATASET
            # =====================================================================
            t0_trans = time.perf_counter()
            res_exec = await client.post(
                f"/api/v1/transformations/pipelines/{pipe_id}/run",
                json={"output_dataset_name": "Enriched Global Sales Output"},
                headers=headers_editor,
            )
            t1_trans = time.perf_counter()
            AUDIT_BENCHMARKS["transformation_duration_ms"] = round((t1_trans - t0_trans) * 1000, 2)
            assert res_exec.status_code == 200, res_exec.text
            run_data = res_exec.json()
            assert run_data["status"] == "completed"
            assert run_data["row_count"] > 0
            derived_dataset_id = run_data["output_dataset_id"]
            assert derived_dataset_id is not None

            # Verify derived dataset schema contains joined columns and calculated column
            res_derived = await client.get(f"/api/v1/datasets/{derived_dataset_id}", headers=headers_editor)
            assert res_derived.status_code == 200
            derived_detail = res_derived.json()
            assert derived_detail["row_count"] > 0
            cur_ver = derived_detail.get("current_version") or {}
            cols = cur_ver.get("schema_metadata", {}).get("columns", []) or derived_detail.get("schema_metadata", {}).get("columns", [])
            derived_col_names = [c["name"] for c in cols]
            assert "net_revenue" in derived_col_names
            assert "customer_tier" in derived_col_names
            assert "country" in derived_col_names

            # =====================================================================
            # DATA INTEGRITY: SOURCE DATASETS REMAIN 100% IMMUTABLE
            # =====================================================================
            async with session_maker() as s:
                v_orders_after = (
                    await s.execute(
                        DatasetVersion.__table__.select().where(DatasetVersion.dataset_id == uuid.UUID(orders_id))
                    )
                ).first()
                v_cust_after = (
                    await s.execute(
                        DatasetVersion.__table__.select().where(DatasetVersion.dataset_id == uuid.UUID(customers_id))
                    )
                ).first()
                assert v_orders_after.checksum == initial_orders_sha
                assert v_orders_after.row_count == 100
                assert v_cust_after.checksum == initial_cust_sha
                assert v_cust_after.row_count == 25

            # =====================================================================
            # 7, 8. CREATE DASHBOARD & MULTIPLE CHART WIDGET TYPES
            # =====================================================================
            dash_payload = {
                "title": "Executive Sales & Operations Dashboard",
                "description": "Cross-functional KPI cards and multi-chart views",
                "visibility": "workspace",
            }
            res_dash = await client.post("/api/v1/dashboards", json=dash_payload, headers=headers_editor)
            assert res_dash.status_code == 201, res_dash.text
            dash_id = res_dash.json()["id"]

            # Widget 1: KPI Card
            w_kpi_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets",
                json={
                    "title": "Total Net Revenue",
                    "widget_type": "kpi",
                    "dataset_id": derived_dataset_id,
                    "grid_x": 0,
                    "grid_y": 0,
                    "grid_w": 4,
                    "grid_h": 2,
                    "query_config": {
                        "metric_column": "net_revenue",
                        "aggregation": "sum",
                    },
                },
                headers=headers_editor,
            )
            assert w_kpi_res.status_code == 201
            w_kpi_id = w_kpi_res.json()["id"]

            # Widget 2: Bar Chart
            w_bar_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets",
                json={
                    "title": "Revenue by Region",
                    "widget_type": "bar",
                    "dataset_id": derived_dataset_id,
                    "grid_x": 4,
                    "grid_y": 0,
                    "grid_w": 8,
                    "grid_h": 3,
                    "query_config": {
                        "group_by_column": "region",
                        "metric_column": "net_revenue",
                        "aggregation": "sum",
                    },
                },
                headers=headers_editor,
            )
            assert w_bar_res.status_code == 201
            w_bar_id = w_bar_res.json()["id"]

            # Widget 3: Line Chart
            w_line_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets",
                json={
                    "title": "Revenue Trend",
                    "widget_type": "line",
                    "dataset_id": derived_dataset_id,
                    "grid_x": 0,
                    "grid_y": 3,
                    "grid_w": 6,
                    "grid_h": 3,
                    "query_config": {
                        "time_column": "order_date",
                        "metric_column": "net_revenue",
                        "aggregation": "sum",
                    },
                },
                headers=headers_editor,
            )
            assert w_line_res.status_code == 201
            w_line_id = w_line_res.json()["id"]

            # Widget 4: Donut Chart
            w_donut_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets",
                json={
                    "title": "Units by Category",
                    "widget_type": "donut",
                    "dataset_id": derived_dataset_id,
                    "grid_x": 6,
                    "grid_y": 3,
                    "grid_w": 6,
                    "grid_h": 3,
                    "query_config": {
                        "group_by_column": "product_category",
                        "metric_column": "units",
                        "aggregation": "sum",
                    },
                },
                headers=headers_editor,
            )
            assert w_donut_res.status_code == 201
            w_donut_id = w_donut_res.json()["id"]

            # Execute Queries & Measure Latencies
            t0_q = time.perf_counter()
            q_kpi_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets/{w_kpi_id}/query",
                json={},
                headers=headers_editor,
            )
            t1_q = time.perf_counter()
            AUDIT_BENCHMARKS["dashboard_query_duration_ms"] = round((t1_q - t0_q) * 1000, 2)
            assert q_kpi_res.status_code == 200
            q_kpi_data = q_kpi_res.json()
            assert q_kpi_data["data"]["value"] > 0

            q_bar_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets/{w_bar_id}/query",
                json={},
                headers=headers_editor,
            )
            assert q_bar_res.status_code == 200
            assert q_bar_res.json()["row_count"] <= 4

            q_line_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets/{w_line_id}/query",
                json={},
                headers=headers_editor,
            )
            assert q_line_res.status_code == 200
            assert q_line_res.json()["row_count"] > 0

            q_donut_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets/{w_donut_id}/query",
                json={},
                headers=headers_editor,
            )
            assert q_donut_res.status_code == 200
            assert q_donut_res.json()["row_count"] > 0

            # =====================================================================
            # 9, 10, 11. DASHBOARD FILTERS & CROSS-FILTERING & DRILL-DOWN
            # =====================================================================
            t0_f = time.perf_counter()
            filter_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets/{w_bar_id}/query",
                json={"filters": [{"column": "region", "operator": "eq", "value": "North America"}]},
                headers=headers_editor,
            )
            t1_f = time.perf_counter()
            AUDIT_BENCHMARKS["filter_response_duration_ms"] = round((t1_f - t0_f) * 1000, 2)
            assert filter_res.status_code == 200
            assert filter_res.json()["row_count"] == 1

            # Cross-filter query with EMEA
            cross_res = await client.post(
                f"/api/v1/dashboards/{dash_id}/widgets/{w_bar_id}/query",
                json={"filters": [{"column": "region", "operator": "eq", "value": "EMEA"}]},
                headers=headers_editor,
            )
            assert cross_res.status_code == 200
            assert cross_res.json()["row_count"] == 1

            # =====================================================================
            # 12. CREATE BUSINESS REPORT USING DASHBOARD
            # =====================================================================
            report_payload = {
                "title": "Q3 Executive Performance Review",
                "description": "Automated report bound to derived Parquet data and dashboard widgets",
                "report_type": "sales",
                "template_id": "sales_perf",
                "configuration": {
                    "period": "Q3 2026",
                    "audience": "Leadership",
                    "sections": [
                        {"id": "cover", "title": "Cover Page", "section_type": "cover", "order": 0},
                        {"id": "summary", "title": "Executive Summary", "section_type": "summary", "order": 1},
                        {"id": "kpis", "title": "Sales KPIs", "section_type": "kpi_grid", "order": 2},
                        {"id": "charts", "title": "Visual Trends", "section_type": "chart_series", "order": 3},
                        {"id": "findings", "title": "Drivers & Insights", "section_type": "findings", "order": 4},
                        {"id": "provenance", "title": "Data Provenance", "section_type": "provenance", "order": 5},
                    ],
                },
                "source_dashboard_ids": [dash_id],
                "source_dataset_refs": [{"dataset_id": derived_dataset_id}],
                "source_model_run_refs": [],
            }
            res_rep = await client.post("/api/v1/reports/business", json=report_payload, headers=headers_editor)
            assert res_rep.status_code == 201, res_rep.text
            rep_data = res_rep.json()
            report_id = rep_data["id"]

            # =====================================================================
            # 13. GENERATE MULTI-FORMAT REPORT OUTPUTS (PDF, DOCX, XLSX, CSV)
            # =====================================================================
            t0_rep = time.perf_counter()
            res_run = await client.post(
                f"/api/v1/reports/business/{report_id}/run",
                json={"formats": ["pdf", "docx", "xlsx", "csv"], "period": "Q3 2026"},
                headers=headers_editor,
            )
            t1_rep = time.perf_counter()
            AUDIT_BENCHMARKS["report_generation_duration_ms"] = round((t1_rep - t0_rep) * 1000, 2)
            assert res_run.status_code in (200, 201), res_run.text
            run_data = res_run.json()
            assert run_data["execution_status"] == "completed"
            run_id = run_data["id"]

            # Download & verify each format
            pdf_res = await client.get(
                f"/api/v1/reports/runs/{run_id}/download?format=pdf",
                headers=headers_editor,
            )
            assert pdf_res.status_code == 200
            assert pdf_res.headers["content-type"] == "application/pdf"
            assert pdf_res.content.startswith(b"%PDF-")

            docx_res = await client.get(
                f"/api/v1/reports/runs/{run_id}/download?format=docx",
                headers=headers_editor,
            )
            assert docx_res.status_code == 200
            assert docx_res.content.startswith(b"PK\x03\x04")

            xlsx_res = await client.get(
                f"/api/v1/reports/runs/{run_id}/download?format=xlsx",
                headers=headers_editor,
            )
            assert xlsx_res.status_code == 200
            assert xlsx_res.content.startswith(b"PK\x03\x04")

            csv_res = await client.get(
                f"/api/v1/reports/runs/{run_id}/download?format=csv",
                headers=headers_editor,
            )
            assert csv_res.status_code == 200
            assert csv_res.text.startswith("#")

            # =====================================================================
            # 14. VERIFY REPORT HISTORY & PROVENANCE
            # =====================================================================
            hist_res = await client.get(f"/api/v1/reports/business/{report_id}/runs", headers=headers_editor)
            assert hist_res.status_code == 200
            runs = hist_res.json()
            assert len(runs) >= 1
            latest_run = runs[0]
            assert latest_run["execution_duration_ms"] > 0
            assert "pdf" in latest_run["generated_files"]

            # Provenance integrity: check dataset version and hash are present
            provenance = latest_run["source_provenance"]
            assert len(provenance) >= 1
            prov_record = provenance[0]
            assert prov_record["dataset_id"] == derived_dataset_id
            assert prov_record.get("manifest_sha256") is not None

            # =====================================================================
            # 15, 16. SCHEDULED REPORT EXECUTION & RESTART RECOVERY
            # =====================================================================
            sched_payload = {
                "frequency": "daily",
                "hour": 8,
                "minute": 0,
                "timezone": "UTC",
                "delivery_configuration": {
                    "recipients": ["leadership@datalens.ai"],
                    "delivery_mode": "email",
                },
            }
            # Verify Editor cannot create schedule (Requires Admin/Owner)
            sched_forbidden = await client.post(
                f"/api/v1/reports/business/{report_id}/schedules",
                json=sched_payload,
                headers=headers_editor,
            )
            assert sched_forbidden.status_code == 403

            # Owner creates schedule
            sched_res = await client.post(
                f"/api/v1/reports/business/{report_id}/schedules",
                json=sched_payload,
                headers=headers_owner,
            )
            assert sched_res.status_code == 201, sched_res.text
            sched_data = sched_res.json()
            sched_id = sched_data["id"]

            # Force schedule to be due right now and trigger execution
            async with session_maker() as s:
                sched_obj = await s.get(ReportSchedule, uuid.UUID(sched_id))
                sched_obj.next_execution_time = datetime.now(UTC)
                await s.commit()

                executed_runs = await ReportSchedulerService.trigger_due_schedules(db=s)
                assert len(executed_runs) >= 1

                # Verify next execution time advanced into the future
                await s.refresh(sched_obj)
                assert sched_obj.last_execution_time is not None
                assert sched_obj.next_execution_time > sched_obj.last_execution_time

                # Simulated restart: no extra runs should execute since schedule is advanced
                due_restart = await ReportSchedulerService.trigger_due_schedules(db=s)
                assert len(due_restart) == 0

            # =====================================================================
            # 17. EMAIL DELIVERY VERIFICATION
            # =====================================================================
            dev_email_adapter.clear()
            email_res = await EmailDeliveryService.deliver_report(
                report_title="Q3 Executive Review",
                recipients=["exec@datalens.ai", "invalid-address"],
                attachments={"report.pdf": pdf_res.content},
                period="Q3 2026",
            )
            assert email_res["success"] is True
            assert email_res["recipients_count"] == 1
            assert len(dev_email_adapter.sent_emails) == 1
            assert dev_email_adapter.sent_emails[0]["to"] == "exec@datalens.ai"

            # =====================================================================
            # SECURITY & WORKSPACE ISOLATION VERIFICATION
            # =====================================================================
            # 1. Foreign workspace user cannot access orders dataset
            res_sec1 = await client.get(f"/api/v1/datasets/{orders_id}", headers=headers_foreign)
            assert res_sec1.status_code in (403, 404)

            # 2. Foreign workspace user cannot access dashboard
            res_sec2 = await client.get(f"/api/v1/dashboards/{dash_id}", headers=headers_foreign)
            assert res_sec2.status_code in (403, 404)

            # 3. Foreign workspace user cannot access transformation pipeline
            res_sec3 = await client.get(
                f"/api/v1/transformations/pipelines/{pipe_id}", headers=headers_foreign
            )
            assert res_sec3.status_code in (403, 404)

            # 4. Foreign workspace user cannot access business report
            res_sec4 = await client.get(f"/api/v1/reports/business/{report_id}", headers=headers_foreign)
            assert res_sec4.status_code in (403, 404)

            # 5. Viewer role cannot create dashboards
            res_sec5 = await client.post(
                "/api/v1/dashboards",
                json={"name": "Viewer Dashboard Attempt"},
                headers=headers_viewer,
            )
            assert res_sec5.status_code == 403

            # 6. Viewer role cannot create transformations
            res_sec6 = await client.post(
                "/api/v1/transformations/pipelines",
                json={"name": "Viewer Pipeline Attempt", "source_dataset_ids": [orders_id]},
                headers=headers_viewer,
            )
            assert res_sec6.status_code == 403

            # 7. Viewer role cannot create reports
            res_sec7 = await client.post(
                "/api/v1/reports/business",
                json=report_payload,
                headers=headers_viewer,
            )
            assert res_sec7.status_code == 403

            # Print benchmark results for audit log
            print("\n=== PHASE 4 BENCHMARK AUDIT RESULTS ===")
            for k, v in AUDIT_BENCHMARKS.items():
                print(f"  {k}: {v} ms")
            print("========================================")

    finally:
        app.dependency_overrides.clear()
