import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.reports.csv_generator import generate_csv_report
from app.services.reports.docx_generator import generate_docx_report
from app.services.reports.pdf_generator import generate_pdf_report
from app.services.reports.xlsx_generator import generate_xlsx_report


@pytest.fixture
def mock_analytics_payload():
    return {
        "profile": {
            "row_count": 12450,
            "column_count": 18,
        },
        "stats": {
            "columns": {
                "revenue": {
                    "count": 12450,
                    "sum": 1240500.0,
                    "mean": 99.64,
                    "median": 85.50,
                    "min": 10.0,
                    "max": 2500.0,
                    "standard_deviation": 45.2,
                },
                "units": {
                    "count": 12450,
                    "sum": 35000.0,
                    "mean": 2.81,
                    "median": 2.0,
                    "min": 1.0,
                    "max": 20.0,
                    "standard_deviation": 1.5,
                },
            }
        },
        "agg": {
            "aggregation": "sum",
            "metric_column": "revenue",
            "group_by_columns": ["product"],
            "items": [
                {"key": "Premium Pro", "value": 583000.0, "count": 5200, "share_of_total": 47.0, "formatted_value": "$583,000.00"},
                {"key": "Basic Plan", "value": 410000.0, "count": 4800, "share_of_total": 33.0, "formatted_value": "$410,000.00"},
            ],
        },
        "quality": {
            "quality_score": 96,
            "issues": [
                {
                    "severity": "low",
                    "title": "Minor Outliers in Revenue",
                    "description": "Found 4 outlier transactions.",
                    "affected_count": 4,
                    "suggested_action": "Verify high-value orders.",
                }
            ],
        },
    }


def test_pdf_report_generation(mock_analytics_payload):
    data = generate_pdf_report(
        title="Q3 Executive Revenue Report",
        dataset_name="Sales_Data_2025",
        version_number="v1.0",
        workspace_name="Acme Corp",
        profile_data=mock_analytics_payload["profile"],
        stats_data=mock_analytics_payload["stats"],
        agg_data=mock_analytics_payload["agg"],
        quality_data=mock_analytics_payload["quality"],
    )
    assert isinstance(data, bytes)
    assert len(data) > 1000
    # PDF magic header %PDF
    assert data.startswith(b"%PDF")


def test_docx_report_generation(mock_analytics_payload):
    data = generate_docx_report(
        title="Operational Performance Report",
        dataset_name="Operations_Data",
        version_number="v2.0",
        workspace_name="Acme Corp",
        profile_data=mock_analytics_payload["profile"],
        stats_data=mock_analytics_payload["stats"],
        agg_data=mock_analytics_payload["agg"],
        quality_data=mock_analytics_payload["quality"],
    )
    assert isinstance(data, bytes)
    assert len(data) > 1000
    # DOCX is a zip file, magic header PK\x03\x04
    assert data.startswith(b"PK\x03\x04")


def test_xlsx_report_generation(mock_analytics_payload):
    data = generate_xlsx_report(
        title="Analytical Metrics Workbook",
        dataset_name="Sales_Data_2025",
        version_number="v1.0",
        workspace_name="Acme Corp",
        profile_data=mock_analytics_payload["profile"],
        stats_data=mock_analytics_payload["stats"],
        agg_data=mock_analytics_payload["agg"],
        quality_data=mock_analytics_payload["quality"],
    )
    assert isinstance(data, bytes)
    assert len(data) > 1000
    # XLSX is a zip file, magic header PK\x03\x04
    assert data.startswith(b"PK\x03\x04")


def test_csv_report_generation(mock_analytics_payload):
    data = generate_csv_report(
        agg_data=mock_analytics_payload["agg"],
        stats_data=mock_analytics_payload["stats"],
    )
    assert isinstance(data, bytes)
    assert len(data) > 0
    text = data.decode("utf-8")
    assert "group_key,value,row_count,share_of_total_pct" in text
    assert "Premium Pro,583000.0,5200,47.0" in text


@pytest.mark.asyncio
async def test_report_endpoints_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/v1/reports without auth
        res = await client.get("/api/v1/reports")
        assert res.status_code == 401

        # POST /api/v1/reports without auth
        res_post = await client.post(
            "/api/v1/reports",
            json={"dataset_id": str(uuid.uuid4()), "title": "Test Report", "format": "pdf"},
        )
        assert res_post.status_code == 401

        # GET /api/v1/reports/{id}/download without auth
        res_dl = await client.get(f"/api/v1/reports/{uuid.uuid4()}/download")
        assert res_dl.status_code == 401
