import csv
import io
from datetime import UTC, datetime

import openpyxl
from docx import Document
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.exceptions import DataLensException
from app.models.model_run import ModelRun


class MLReportService:
    """
    Generates downloadable reports (PDF, DOCX, XLSX, CSV) for ML model runs.
    Contains algorithm parameters, version provenance, metrics, tables, and caveats.
    """

    @classmethod
    def generate_report(
        cls,
        model_run: ModelRun,
        report_format: str = "pdf",
    ) -> tuple[bytes, str, str]:
        """
        Returns: (file_bytes, media_type, filename)
        """
        fmt = report_format.lower().strip()
        filename = f"datalens_{model_run.model_type}_{model_run.id.hex[:8]}.{fmt}"

        if fmt == "pdf":
            data = cls._generate_pdf(model_run)
            return data, "application/pdf", filename
        elif fmt == "docx":
            data = cls._generate_docx(model_run)
            return data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename
        elif fmt == "xlsx":
            data = cls._generate_xlsx(model_run)
            return data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename
        elif fmt == "csv":
            data = cls._generate_csv(model_run)
            return data, "text/csv", filename
        else:
            raise DataLensException(f"Unsupported report format '{fmt}'. Choose pdf, docx, xlsx, or csv.", code="INVALID_FORMAT")

    @classmethod
    def _generate_pdf(cls, run: ModelRun) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "MLTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#102C46"),
            spaceAfter=8,
        )
        meta_style = ParagraphStyle(
            "MLMeta",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#52616C"),
            spaceAfter=12,
        )
        heading_style = ParagraphStyle(
            "MLHeading",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#009F98"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "MLBody",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#102C46"),
            spaceAfter=6,
            leading=12,
        )

        elements = []
        # Title
        display_type = run.model_type.replace("_", " ").title()
        elements.append(Paragraph(f"DataLens {display_type} Report", title_style))
        elements.append(
            Paragraph(
                f"Algorithm: <b>{run.algorithm.upper()}</b> | Model Run ID: {run.id} | Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                meta_style,
            )
        )
        elements.append(Spacer(1, 10))

        # Model Provenance Table
        elements.append(Paragraph("1. Model Run Provenance", heading_style))
        summary = run.result_summary or {}
        prov_data = [
            ["Dataset ID", str(run.dataset_id)],
            ["Dataset Version ID", str(run.dataset_version_id)],
            ["Features Evaluated", ", ".join(run.feature_columns)],
            ["Execution Duration", f"{run.duration_ms} ms"],
        ]
        t = Table(prov_data, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF7FA")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#102C46")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Verified Metrics
        elements.append(Paragraph("2. Evaluated Metrics & Outcomes", heading_style))
        metrics = run.metrics or {}
        metric_rows = [["Metric", "Value"]]
        for k, v in metrics.items():
            metric_rows.append([k.replace("_", " ").title(), str(v)])
        t_m = Table(metric_rows, colWidths=[200, 300])
        t_m.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102C46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_m)
        elements.append(Spacer(1, 12))

        # Caveats & Limitations
        elements.append(Paragraph("3. Analytical Caveats & Governance", heading_style))
        caveats = summary.get("caveats_and_limitations", [])
        if caveats:
            for c in caveats:
                elements.append(Paragraph(f"• {c}", body_style))
        else:
            elements.append(Paragraph("Standard statistical limitations apply.", body_style))

        doc.build(elements)
        return buf.getvalue()

    @classmethod
    def _generate_docx(cls, run: ModelRun) -> bytes:
        doc = Document()
        display_type = run.model_type.replace("_", " ").title()
        doc.add_heading(f"DataLens {display_type} Report", level=1)
        p = doc.add_paragraph()
        p.add_run(f"Algorithm: {run.algorithm.upper()}\n").bold = True
        p.add_run(f"Run ID: {run.id}\n")
        p.add_run(f"Generated at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        doc.add_heading("Model Run Provenance", level=2)
        table = doc.add_table(rows=1, cols=2)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Parameter"
        hdr_cells[1].text = "Value"

        prov = [
            ("Dataset ID", str(run.dataset_id)),
            ("Dataset Version ID", str(run.dataset_version_id)),
            ("Features", ", ".join(run.feature_columns)),
            ("Execution Time", f"{run.duration_ms} ms"),
        ]
        for k, v in prov:
            row_cells = table.add_row().cells
            row_cells[0].text = k
            row_cells[1].text = v

        doc.add_heading("Model Metrics", level=2)
        m_table = doc.add_table(rows=1, cols=2)
        m_table.rows[0].cells[0].text = "Metric"
        m_table.rows[0].cells[1].text = "Value"
        for k, v in (run.metrics or {}).items():
            r = m_table.add_row().cells
            r[0].text = str(k)
            r[1].text = str(v)

        doc.add_heading("Caveats & Limitations", level=2)
        caveats = (run.result_summary or {}).get("caveats_and_limitations", [])
        for c in caveats:
            doc.add_paragraph(c, style="List Bullet")

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    @classmethod
    def _generate_xlsx(cls, run: ModelRun) -> bytes:
        wb = openpyxl.Workbook()
        ws_summary = wb.active
        ws_summary.title = "Summary"

        ws_summary.append(["DataLens ML Analysis Report"])
        ws_summary.append(["Model Type", run.model_type])
        ws_summary.append(["Algorithm", run.algorithm])
        ws_summary.append(["Run ID", str(run.id)])
        ws_summary.append(["Dataset ID", str(run.dataset_id)])
        ws_summary.append(["Version ID", str(run.dataset_version_id)])
        ws_summary.append(["Generated At", datetime.now(UTC).isoformat()])
        ws_summary.append([])

        ws_summary.append(["Metric", "Value"])
        for k, v in (run.metrics or {}).items():
            ws_summary.append([k, str(v)])

        # Data Sheet
        summary = run.result_summary or {}
        if run.model_type == "anomaly_detection":
            ws_anom = wb.create_sheet("Anomalies")
            ws_anom.append(["Row Index", "Timestamp", "Actual Value", "Expected Value", "Anomaly Score", "Severity"])
            for pt in summary.get("anomalous_points", []):
                ws_anom.append([
                    pt.get("row_index"),
                    pt.get("timestamp"),
                    pt.get("actual_value"),
                    pt.get("expected_value"),
                    pt.get("anomaly_score"),
                    pt.get("severity"),
                ])
        elif run.model_type == "forecasting":
            ws_fc = wb.create_sheet("Forecast")
            ws_fc.append(["Period", "Timestamp", "Forecast Value", "Lower Bound", "Upper Bound"])
            for pt in summary.get("forecast_points", []):
                ws_fc.append([
                    pt.get("period_index"),
                    pt.get("timestamp"),
                    pt.get("forecast_value"),
                    pt.get("lower_bound"),
                    pt.get("upper_bound"),
                ])
        elif run.model_type == "segmentation":
            ws_seg = wb.create_sheet("Clusters")
            ws_seg.append(["Cluster ID", "Name", "Record Count", "Percentage", "Characterization"])
            for c in summary.get("clusters", []):
                ws_seg.append([
                    c.get("cluster_id"),
                    c.get("cluster_name"),
                    c.get("record_count"),
                    c.get("percentage"),
                    c.get("characterization"),
                ])

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @classmethod
    def _generate_csv(cls, run: ModelRun) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)
        summary = run.result_summary or {}

        if run.model_type == "anomaly_detection":
            writer.writerow(["row_index", "timestamp", "actual_value", "expected_value", "anomaly_score", "severity"])
            for pt in summary.get("anomalous_points", []):
                writer.writerow([
                    pt.get("row_index"),
                    pt.get("timestamp"),
                    pt.get("actual_value"),
                    pt.get("expected_value"),
                    pt.get("anomaly_score"),
                    pt.get("severity"),
                ])
        elif run.model_type == "forecasting":
            writer.writerow(["period_index", "timestamp", "forecast_value", "lower_bound", "upper_bound"])
            for pt in summary.get("forecast_points", []):
                writer.writerow([
                    pt.get("period_index"),
                    pt.get("timestamp"),
                    pt.get("forecast_value"),
                    pt.get("lower_bound"),
                    pt.get("upper_bound"),
                ])
        elif run.model_type == "segmentation":
            writer.writerow(["cluster_id", "cluster_name", "record_count", "percentage", "characterization"])
            for c in summary.get("clusters", []):
                writer.writerow([
                    c.get("cluster_id"),
                    c.get("cluster_name"),
                    c.get("record_count"),
                    c.get("percentage"),
                    c.get("characterization"),
                ])
        else:
            writer.writerow(["metric", "value"])
            for k, v in (run.metrics or {}).items():
                writer.writerow([k, v])

        return buf.getvalue().encode("utf-8")
