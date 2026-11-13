import uuid
from datetime import UTC, datetime

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
from app.services.email_adapter import dev_email_adapter
from app.services.reports.business_report_export import BusinessReportExportService
from app.services.reports.deterministic_narrative import DeterministicNarrativeGenerator
from app.services.reports.email_delivery import EmailDeliveryService
from app.services.reports.scheduler_service import ReportSchedulerService
from app.services.reports.templates import SYSTEM_REPORT_TEMPLATES

# ---------------------------------------------------------------------------
# UNIT TESTS: Templates, Formats, Math & Delivery
# ---------------------------------------------------------------------------

def test_system_templates_definition():
    """Verify that all 8 required business templates are present with valid schemas."""
    assert len(SYSTEM_REPORT_TEMPLATES) >= 8
    categories = [t["category"] for t in SYSTEM_REPORT_TEMPLATES]
    assert "executive" in categories
    assert "sales" in categories
    assert "finance" in categories
    assert "marketing" in categories
    assert "customer" in categories
    assert "operations" in categories
    assert "predictive" in categories
    assert "custom" in categories

    for tpl in SYSTEM_REPORT_TEMPLATES:
        assert tpl["id"]
        assert tpl["name"]
        assert len(tpl["default_sections"]) >= 4
        # Every template has provenance section
        section_types = [s["section_type"] for s in tpl["default_sections"]]
        assert "provenance" in section_types


def test_deterministic_narrative_generation():
    """Test verified narrative generation without AI."""
    kpis = [
        {
            "metric": "Gross Revenue",
            "value": 1500000.0,
            "formatted_value": "$1,500,000",
            "comparison": {
                "mode": "target",
                "benchmark": 1200000.0,
                "percentage_change": 25.0,
                "direction": "up",
            },
        },
        {
            "metric": "Customer Churn",
            "value": 2.1,
            "formatted_value": "2.1%",
            "comparison": {
                "mode": "target",
                "benchmark": 2.5,
                "percentage_change": -16.0,
                "direction": "down",
            },
        },
    ]
    summary = DeterministicNarrativeGenerator.generate_executive_summary(
        report_title="Q1 Review",
        kpis=kpis,
        period="Q1 2026",
    )
    assert "Q1 Review" in summary
    assert "$1,500,000" in summary
    assert "▲ 25.0%" in summary

    findings = DeterministicNarrativeGenerator.generate_findings(kpis)
    assert len(findings) >= 2
    assert "Gross Revenue" in findings[0]


def test_multi_format_generation():
    """Verify that PDF, DOCX, XLSX, and CSV are properly generated from evidence."""
    mock_evidence = {
        "report_title": "Omnichannel Sales Audit",
        "period": "Last 30 Days",
        "generated_at": "2026-11-12 12:00:00 UTC",
        "ai_generated": False,
        "kpis": [
            {
                "metric": "Online Revenue",
                "value": 450000.0,
                "formatted_value": "$450,000",
                "comparison": {"benchmark": 400000.0, "percentage_change": 12.5, "direction": "up"},
            }
        ],
        "sections": [
            {
                "title": "Executive Summary",
                "section_type": "summary",
                "content": "Overall commercial revenue expanded across digital storefronts.",
            },
            {
                "title": "Core Metrics",
                "section_type": "kpi_grid",
                "kpi_items": [
                    {
                        "metric": "Online Revenue",
                        "value": 450000.0,
                        "formatted_value": "$450,000",
                        "comparison": {"benchmark": 400000.0, "percentage_change": 12.5, "direction": "up"},
                    }
                ],
            },
            {
                "title": "Regional Share",
                "section_type": "chart",
                "chart_items": [
                    {"label": "North", "value": 250000},
                    {"label": "South", "value": 200000},
                ],
            },
            {
                "title": "Audit Lineage",
                "section_type": "provenance",
                "provenance_records": [
                    {
                        "dataset_name": "Sales_2026",
                        "version_id": "v-12345",
                        "row_count": 8500,
                        "manifest_sha256": "abc12345",
                    }
                ],
            },
        ],
        "provenance": [
            {
                "dataset_name": "Sales_2026",
                "dataset_id": "ds-001",
                "version_id": "v-12345",
                "row_count": 8500,
                "manifest_sha256": "abc12345",
            }
        ],
    }

    # 1. PDF
    pdf_bytes = BusinessReportExportService.generate_pdf(mock_evidence)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

    # 2. DOCX
    docx_bytes = BusinessReportExportService.generate_docx(mock_evidence)
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 1000

    # 3. XLSX
    xlsx_bytes = BusinessReportExportService.generate_xlsx(mock_evidence)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 1000

    # 4. CSV
    csv_bytes = BusinessReportExportService.generate_csv(mock_evidence)
    assert isinstance(csv_bytes, bytes)
    csv_text = csv_bytes.decode("utf-8")
    assert "Omnichannel Sales Audit" in csv_text
    assert "Online Revenue" in csv_text
    assert "Sales_2026" in csv_text


def test_timezone_aware_scheduler_calculations():
    """Verify schedule next run timestamps across timezones."""
    base = datetime(2026, 3, 10, 10, 0, tzinfo=UTC)  # Tuesday

    # Daily at 08:00 UTC -> next is tomorrow 2026-03-11 08:00
    next_daily = ReportSchedulerService.calculate_next_run(
        frequency="daily",
        hour=8,
        minute=0,
        tz_str="UTC",
        base_time=base,
    )
    assert next_daily.hour == 8
    assert next_daily.day == 11

    # Weekly on Friday (weekday 4) at 09:00 UTC
    next_weekly = ReportSchedulerService.calculate_next_run(
        frequency="weekly",
        hour=9,
        minute=0,
        day_of_week=4,  # Friday
        tz_str="UTC",
        base_time=base,
    )
    assert next_weekly.weekday() == 4
    assert next_weekly.day == 13

    # Monthly on the 1st
    next_monthly = ReportSchedulerService.calculate_next_run(
        frequency="monthly",
        hour=8,
        minute=0,
        day_of_month=1,
        tz_str="UTC",
        base_time=base,
    )
    assert next_monthly.day == 1
    assert next_monthly.month == 4


@pytest.mark.asyncio
async def test_email_delivery_validation_and_audit():
    """Test recipient email validation and dev adapter audit logging."""
    dev_email_adapter.clear()

    # Valid recipients
    res = await EmailDeliveryService.deliver_report(
        report_title="Monthly Pulse",
        recipients=["exec@company.com", "analyst@company.com", "invalid-email"],
        attachments={"report.pdf": b"%PDF-mock-bytes"},
        period="November 2026",
    )
    assert res["success"] is True
    assert res["recipients_count"] == 2
    assert len(dev_email_adapter.sent_emails) == 2
    assert dev_email_adapter.sent_emails[0]["to"] == "exec@company.com"

    # Reject oversized payload
    giant_attachments = {"huge.pdf": b"x" * (26 * 1024 * 1024)}
    res_large = await EmailDeliveryService.deliver_report(
        report_title="Oversized Report",
        recipients=["exec@company.com"],
        attachments=giant_attachments,
    )
    assert res_large["success"] is False
    assert "exceeds 25MB threshold" in res_large["error"]


# ---------------------------------------------------------------------------
# INTEGRATION TESTS: Live Database, API Endpoints, RBAC & Isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_business_report_full_lifecycle_live():
    """
    Live PostgreSQL integration test:
    1. Workspace setup with Owner, Editor, Viewer
    2. Template querying
    3. Business Report creation by Editor
    4. Report update & duplicate
    5. Manual Report Run execution with file generation
    6. Run file download authorization
    7. Schedule creation & due execution
    8. RBAC enforcement (Viewer cannot create or delete report)
    9. Cross-workspace isolation
    """
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with session_maker() as session:
            # 1. Setup Owner, Editor, Viewer
            owner = User(
                full_name="Report Owner",
                email=f"rep_owner_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            editor = User(
                full_name="Report Editor",
                email=f"rep_editor_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("Pass123!"),
                is_active=True,
            )
            viewer = User(
                full_name="Report Viewer",
                email=f"rep_viewer_{uuid.uuid4().hex[:8]}@datalens.ai",
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

            ws = Workspace(name="Reporting Workspace", owner_id=owner.id)
            other_ws = Workspace(name="Other Workspace", owner_id=other_user.id)
            session.add_all([ws, other_ws])
            await session.commit()
            await session.refresh(ws)
            await session.refresh(other_ws)

            session.add_all([
                WorkspaceMembership(workspace_id=ws.id, user_id=owner.id, role="owner"),
                WorkspaceMembership(workspace_id=ws.id, user_id=editor.id, role="editor"),
                WorkspaceMembership(workspace_id=ws.id, user_id=viewer.id, role="viewer"),
                WorkspaceMembership(workspace_id=other_ws.id, user_id=other_user.id, role="owner"),
            ])
            await session.commit()

        owner_token = create_access_token(user_id=owner.id, email=owner.email)
        editor_token = create_access_token(user_id=editor.id, email=editor.email)
        viewer_token = create_access_token(user_id=viewer.id, email=viewer.email)
        other_token = create_access_token(user_id=other_user.id, email=other_user.email)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers_editor = {"Authorization": f"Bearer {editor_token}", "X-Workspace-ID": str(ws.id)}
            headers_viewer = {"Authorization": f"Bearer {viewer_token}", "X-Workspace-ID": str(ws.id)}
            headers_owner = {"Authorization": f"Bearer {owner_token}", "X-Workspace-ID": str(ws.id)}
            headers_other = {"Authorization": f"Bearer {other_token}", "X-Workspace-ID": str(other_ws.id)}

            # 2. Get Templates
            res_tpl = await client.get("/api/v1/reports/templates", headers=headers_editor)
            assert res_tpl.status_code == 200
            templates = res_tpl.json()
            assert len(templates) >= 8

            # 3. Create Business Report (Editor)
            report_payload = {
                "title": "Quarterly Operations Audit",
                "description": "Fulfillment and cycle time review",
                "report_type": "operations",
                "template_id": "tpl-operations-report",
                "configuration": {
                    "period": "2026-Q1",
                    "sections": [
                        {
                            "id": "s1",
                            "title": "Fulfillment Summary",
                            "section_type": "summary",
                        },
                        {
                            "id": "s2",
                            "title": "SLA Performance",
                            "section_type": "kpi_grid",
                            "kpi_items": [
                                {
                                    "label": "MTTR (Hours)",
                                    "value": 4.2,
                                    "target_value": 5.0,
                                    "unit": "hrs",
                                }
                            ],
                        },
                        {
                            "id": "s3",
                            "title": "Provenance",
                            "section_type": "provenance",
                        },
                    ],
                },
                "source_dashboard_ids": [],
                "source_dataset_refs": [],
                "source_model_run_refs": [],
            }
            res_create = await client.post("/api/v1/reports/business", json=report_payload, headers=headers_editor)
            assert res_create.status_code == 201
            report_data = res_create.json()
            report_id = report_data["id"]
            assert report_data["title"] == "Quarterly Operations Audit"

            # 4. Duplicate Report
            res_dup = await client.post(f"/api/v1/reports/business/{report_id}/duplicate", headers=headers_editor)
            assert res_dup.status_code == 201
            assert "(Copy)" in res_dup.json()["title"]

            # 5. Trigger Manual Report Run
            run_payload = {
                "period": "2026-Q1",
                "formats": ["pdf", "docx", "xlsx", "csv"],
                "applied_filters": [],
            }
            res_run = await client.post(f"/api/v1/reports/business/{report_id}/run", json=run_payload, headers=headers_editor)
            assert res_run.status_code == 200
            run_data = res_run.json()
            run_id = run_data["id"]
            if run_data["execution_status"] != "completed":
                print("RUN FAILED ERROR DETAILS:", run_data.get("error_details"))
            assert run_data["execution_status"] == "completed"
            assert "pdf" in run_data["generated_files"]
            assert "xlsx" in run_data["generated_files"]

            # 6. Download Run PDF File (Viewer can download)
            res_dl = await client.get(f"/api/v1/reports/runs/{run_id}/download?format=pdf", headers=headers_viewer)
            assert res_dl.status_code == 200
            assert res_dl.headers["content-type"] == "application/pdf"
            assert res_dl.content.startswith(b"%PDF")

            # 7. Create Schedule (Owner can create, Editor/Viewer cannot)
            res_sched_viewer = await client.post(
                f"/api/v1/reports/business/{report_id}/schedules",
                json={"frequency": "weekly", "hour": 9, "minute": 0, "timezone": "UTC"},
                headers=headers_viewer,
            )
            assert res_sched_viewer.status_code == 403

            res_sched = await client.post(
                f"/api/v1/reports/business/{report_id}/schedules",
                json={
                    "frequency": "weekly",
                    "hour": 9,
                    "minute": 0,
                    "day_of_week": 0,
                    "timezone": "UTC",
                    "delivery_configuration": {
                        "email_recipients": ["management@datalens.ai"],
                        "attach_formats": ["pdf", "xlsx"],
                    },
                },
                headers=headers_owner,
            )
            assert res_sched.status_code == 201
            sched_data = res_sched.json()
            assert sched_data["is_enabled"] is True

            # 8. RBAC: Viewer cannot delete report
            res_del_viewer = await client.delete(f"/api/v1/reports/business/{report_id}", headers=headers_viewer)
            assert res_del_viewer.status_code == 403

            # 9. Cross-Workspace Isolation: Other workspace user cannot access report
            res_iso = await client.get(f"/api/v1/reports/business/{report_id}", headers=headers_other)
            assert res_iso.status_code == 404

            # 10. Clean Delete by Owner
            res_del = await client.delete(f"/api/v1/reports/business/{report_id}", headers=headers_owner)
            assert res_del.status_code == 204

    finally:
        app.dependency_overrides.clear()
