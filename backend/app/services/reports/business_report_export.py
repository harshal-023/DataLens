import csv
import io
from typing import Any

import docx
import openpyxl
from docx.shared import Inches, Pt, RGBColor
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class BusinessReportExportService:
    """
    Multi-format export service for DataLens Business Reports.
    Transforms assembled report evidence into professional PDF, DOCX, XLSX, and CSV documents.
    """

    # -------------------------------------------------------------------------
    # PDF GENERATION
    # -------------------------------------------------------------------------
    @classmethod
    def generate_pdf(cls, evidence: dict[str, Any]) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        teal = colors.HexColor("#009F98")
        deep_navy = colors.HexColor("#102C46")
        cool_grey = colors.HexColor("#52616C")
        bg_light = colors.HexColor("#F5F8FA")

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=deep_navy,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "ReportSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=cool_grey,
            spaceAfter=14,
        )
        heading_style = ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=deep_navy,
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=deep_navy,
            spaceAfter=6,
        )
        bullet_style = ParagraphStyle(
            "ReportBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=deep_navy,
            leftIndent=12,
            spaceAfter=4,
        )

        story = []

        # Cover / Header Banner
        title = evidence.get("report_title", "Business Report")
        period = evidence.get("period", "Current Reporting Period")
        gen_time = evidence.get("generated_at", "")
        ai_badge = " [AI-Assisted Narrative]" if evidence.get("ai_generated") else " [Deterministic Verified]"

        story.append(Paragraph(title, title_style))
        story.append(
            Paragraph(
                f"Reporting Window: <b>{period}</b> | Generated: <b>{gen_time}</b>{ai_badge}",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=2, color=teal, spaceAfter=14))

        # Iterate Sections
        sections = evidence.get("sections", [])
        for idx, sec in enumerate(sections, start=1):
            sec_title = sec.get("title", f"Section {idx}")
            sec_type = sec.get("section_type", "custom")

            story.append(Paragraph(f"{idx}. {sec_title}", heading_style))

            if sec_type == "summary":
                content = sec.get("content", "")
                if content:
                    for para in content.split("\n\n"):
                        if para.strip():
                            story.append(Paragraph(para.replace("\n", " "), body_style))
                else:
                    story.append(Paragraph("No executive narrative provided.", body_style))

            elif sec_type == "kpi_grid":
                kpis = sec.get("kpi_items", [])
                if kpis:
                    table_data = [["Metric", "Current Value", "Benchmark / Variance", "Trend"]]
                    for k in kpis:
                        comp = k.get("comparison")
                        variance_str = "-"
                        trend_str = "■ Flat"
                        if comp:
                            pct = comp.get("percentage_change", 0.0)
                            direction = comp.get("direction", "flat")
                            variance_str = f"{comp.get('benchmark')} ({pct:+.1f}%)"
                            trend_str = "▲ Expansion" if direction == "up" else "▼ Contraction" if direction == "down" else "■ Flat"

                        table_data.append([
                            k.get("metric", "KPI"),
                            str(k.get("formatted_value") or k.get("value")),
                            variance_str,
                            trend_str,
                        ])

                    t = Table(table_data, colWidths=[180, 120, 140, 100])
                    t.setStyle(
                        TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ])
                    )
                    story.append(t)

            elif sec_type == "chart":
                chart_items = sec.get("chart_items", [])
                if chart_items:
                    table_data = [["Category / Series", "Metric Total", "Relative Proportional Share"]]
                    tot = sum(item.get("value", 0) for item in chart_items) or 1.0
                    for item in chart_items[:10]:
                        val = item.get("value", 0)
                        pct = (val / tot) * 100
                        table_data.append([
                            str(item.get("label")),
                            f"{val:,.2f}" if isinstance(val, (int, float)) else str(val),
                            f"{pct:.1f}%",
                        ])

                    t = Table(table_data, colWidths=[240, 150, 150])
                    t.setStyle(
                        TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), teal),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ])
                    )
                    story.append(t)

            elif sec_type == "findings":
                findings = sec.get("findings", [])
                for f in findings:
                    story.append(Paragraph(f"• <b>Observed Finding:</b> {f}", bullet_style))

            elif sec_type == "recommendations":
                recs = sec.get("recommendations", [])
                for r in recs:
                    story.append(Paragraph(f"✓ <b>Recommendation:</b> {r}", bullet_style))

            elif sec_type == "table":
                cols = sec.get("columns", [])[:6]
                rows = sec.get("rows", [])[:15]
                if cols and rows:
                    table_data = [cols]
                    for r in rows:
                        row_vals = [str(r.get(c, ""))[:25] for c in cols]
                        table_data.append(row_vals)

                    col_w = min(540 / len(cols), 120)
                    t = Table(table_data, colWidths=[col_w] * len(cols))
                    t.setStyle(
                        TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C4257")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 7),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ])
                    )
                    story.append(t)

            elif sec_type == "provenance":
                prov = sec.get("provenance_records", [])
                if prov:
                    table_data = [["Dataset Name", "Version ID", "Total Records", "Storage Integrity"]]
                    for p in prov:
                        table_data.append([
                            str(p.get("dataset_name")),
                            str(p.get("version_id"))[:12] + "...",
                            f"{p.get('row_count', 0):,}",
                            str(p.get("manifest_sha256", "verified"))[:12],
                        ])

                    t = Table(table_data, colWidths=[180, 140, 110, 110])
                    t.setStyle(
                        TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#39C3B8")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), deep_navy),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 7),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ])
                    )
                    story.append(t)

            elif sec_type == "limitations":
                limits = sec.get("limitations", [])
                for limit_item in limits:
                    story.append(Paragraph(f"⚠ {limit_item}", bullet_style))

            story.append(Spacer(1, 10))

        # Build document
        doc.build(story)
        return buf.getvalue()

    # -------------------------------------------------------------------------
    # DOCX GENERATION
    # -------------------------------------------------------------------------
    @classmethod
    def generate_docx(cls, evidence: dict[str, Any]) -> bytes:
        doc = docx.Document()

        # Margins
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        title = evidence.get("report_title", "Business Report")
        period = evidence.get("period", "Current Period")
        gen_time = evidence.get("generated_at", "")

        # Title
        h1 = doc.add_heading(title, level=0)
        h1.runs[0].font.color.rgb = RGBColor(16, 44, 70)  # #102C46 Deep Navy
        h1.runs[0].font.size = Pt(22)

        p_meta = doc.add_paragraph()
        p_meta.add_run(f"Period: {period}  |  Generated: {gen_time}  |  DataLens Intelligence").italic = True

        sections = evidence.get("sections", [])
        for idx, sec in enumerate(sections, start=1):
            sec_title = sec.get("title", f"Section {idx}")
            sec_type = sec.get("section_type", "custom")

            h2 = doc.add_heading(f"{idx}. {sec_title}", level=1)
            h2.runs[0].font.color.rgb = RGBColor(0, 159, 152)  # #009F98 Peacock Teal

            if sec_type == "summary":
                content = sec.get("content", "")
                for para in content.split("\n\n"):
                    if para.strip():
                        doc.add_paragraph(para.replace("\n", " "))

            elif sec_type == "kpi_grid":
                kpis = sec.get("kpi_items", [])
                if kpis:
                    table = doc.add_table(rows=1, cols=4)
                    table.style = "Table Grid"
                    hdr = table.rows[0].cells
                    hdr[0].text = "Metric"
                    hdr[1].text = "Value"
                    hdr[2].text = "Benchmark"
                    hdr[3].text = "Variance"

                    for k in kpis:
                        row = table.add_row().cells
                        row[0].text = str(k.get("metric"))
                        row[1].text = str(k.get("formatted_value") or k.get("value"))
                        comp = k.get("comparison")
                        if comp:
                            row[2].text = str(comp.get("benchmark"))
                            row[3].text = f"{comp.get('percentage_change', 0):+.1f}%"
                        else:
                            row[2].text = "-"
                            row[3].text = "-"

            elif sec_type == "chart":
                chart_items = sec.get("chart_items", [])
                if chart_items:
                    table = doc.add_table(rows=1, cols=2)
                    table.style = "Table Grid"
                    table.rows[0].cells[0].text = "Category"
                    table.rows[0].cells[1].text = "Value"
                    for item in chart_items[:10]:
                        row = table.add_row().cells
                        row[0].text = str(item.get("label"))
                        row[1].text = str(item.get("value"))

            elif sec_type == "findings":
                for f in sec.get("findings", []):
                    doc.add_paragraph(f"• {f}", style="List Bullet")

            elif sec_type == "recommendations":
                for r in sec.get("recommendations", []):
                    doc.add_paragraph(f"✓ {r}", style="List Bullet")

            elif sec_type == "table":
                cols = sec.get("columns", [])[:6]
                rows = sec.get("rows", [])[:15]
                if cols and rows:
                    table = doc.add_table(rows=1, cols=len(cols))
                    table.style = "Table Grid"
                    for i, c in enumerate(cols):
                        table.rows[0].cells[i].text = str(c)
                    for r in rows:
                        row = table.add_row().cells
                        for i, c in enumerate(cols):
                            row[i].text = str(r.get(c, ""))[:30]

            elif sec_type == "provenance":
                for p in sec.get("provenance_records", []):
                    doc.add_paragraph(
                        f"Dataset: {p.get('dataset_name')} (Version: {p.get('version_id')}, Records: {p.get('row_count'):,})"
                    )

            elif sec_type == "limitations":
                for limit_item in sec.get("limitations", []):
                    doc.add_paragraph(f"• {limit_item}")

            doc.add_paragraph()  # spacer

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    # -------------------------------------------------------------------------
    # XLSX GENERATION
    # -------------------------------------------------------------------------
    @classmethod
    def generate_xlsx(cls, evidence: dict[str, Any]) -> bytes:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default sheet

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="102C46", end_color="102C46", fill_type="solid")
        teal_fill = PatternFill(start_color="009F98", end_color="009F98", fill_type="solid")
        title_font = Font(name="Calibri", size=14, bold=True, color="102C46")

        # 1. Executive Summary Sheet
        ws_sum = wb.create_sheet(title="Executive Summary")
        ws_sum["A1"] = evidence.get("report_title", "Business Report")
        ws_sum["A1"].font = title_font
        ws_sum["A2"] = f"Period: {evidence.get('period')} | Generated: {evidence.get('generated_at')}"

        row_idx = 4
        sections = evidence.get("sections", [])
        for sec in sections:
            if sec.get("section_type") == "summary":
                ws_sum.cell(row=row_idx, column=1, value="Executive Narrative:").font = Font(bold=True)
                row_idx += 1
                for para in sec.get("content", "").split("\n\n"):
                    if para.strip():
                        ws_sum.cell(row=row_idx, column=1, value=para.strip())
                        row_idx += 1
            elif sec.get("section_type") == "findings":
                ws_sum.cell(row=row_idx, column=1, value="Core Findings:").font = Font(bold=True)
                row_idx += 1
                for f in sec.get("findings", []):
                    ws_sum.cell(row=row_idx, column=1, value=f"• {f}")
                    row_idx += 1
            elif sec.get("section_type") == "recommendations":
                ws_sum.cell(row=row_idx, column=1, value="Strategic Recommendations:").font = Font(bold=True)
                row_idx += 1
                for r in sec.get("recommendations", []):
                    ws_sum.cell(row=row_idx, column=1, value=f"✓ {r}")
                    row_idx += 1

        # 2. KPI Summary Sheet
        ws_kpi = wb.create_sheet(title="KPI Metrics")
        ws_kpi.append(["Metric Name", "Value", "Formatted Value", "Benchmark Target", "Delta Variance", "% Change", "Direction"])
        for col_num in range(1, 8):
            cell = ws_kpi.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill

        kpis = evidence.get("kpis", [])
        for k in kpis:
            comp = k.get("comparison") or {}
            ws_kpi.append([
                k.get("metric"),
                k.get("value"),
                k.get("formatted_value"),
                comp.get("benchmark", "-"),
                comp.get("delta", "-"),
                comp.get("percentage_change", "-"),
                comp.get("direction", "-"),
            ])

        # 3. Chart Breakdown Sheet
        ws_charts = wb.create_sheet(title="Analytical Breakdowns")
        ws_charts.append(["Section", "Category / Label", "Value"])
        for col_num in range(1, 4):
            cell = ws_charts.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = teal_fill

        for sec in sections:
            if sec.get("section_type") == "chart":
                for item in sec.get("chart_items", []):
                    ws_charts.append([sec.get("title"), item.get("label"), item.get("value")])

        # 4. Tabular Data Sheet
        for sec in sections:
            if sec.get("section_type") == "table":
                cols = sec.get("columns", [])
                rows = sec.get("rows", [])
                if cols and rows:
                    ws_tbl = wb.create_sheet(title=sec.get("title", "Data")[:25])
                    ws_tbl.append(cols)
                    for col_num in range(1, len(cols) + 1):
                        cell = ws_tbl.cell(row=1, column=col_num)
                        cell.font = header_font
                        cell.fill = header_fill
                    for r in rows:
                        ws_tbl.append([r.get(c) for c in cols])
                    break

        # 5. Provenance Sheet
        ws_prov = wb.create_sheet(title="Data Lineage")
        ws_prov.append(["Dataset Name", "Dataset ID", "Version ID", "Total Records", "Storage Integrity"])
        for col_num in range(1, 6):
            cell = ws_prov.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill

        for p in evidence.get("provenance", []):
            ws_prov.append([
                p.get("dataset_name"),
                p.get("dataset_id"),
                p.get("version_id"),
                p.get("row_count"),
                p.get("manifest_sha256"),
            ])

        # Auto-fit columns
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # -------------------------------------------------------------------------
    # CSV GENERATION
    # -------------------------------------------------------------------------
    @classmethod
    def generate_csv(cls, evidence: dict[str, Any]) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)

        # Header metadata
        writer.writerow(["# DataLens Business Report Export"])
        writer.writerow(["# Report Title", evidence.get("report_title")])
        writer.writerow(["# Period", evidence.get("period")])
        writer.writerow(["# Generated At", evidence.get("generated_at")])
        writer.writerow([])

        # KPIs Section
        writer.writerow(["--- KEY PERFORMANCE INDICATORS ---"])
        writer.writerow(["Metric", "Value", "Formatted Value", "Benchmark", "Delta", "% Change", "Direction"])
        for k in evidence.get("kpis", []):
            comp = k.get("comparison") or {}
            writer.writerow([
                k.get("metric"),
                k.get("value"),
                k.get("formatted_value"),
                comp.get("benchmark", ""),
                comp.get("delta", ""),
                comp.get("percentage_change", ""),
                comp.get("direction", ""),
            ])
        writer.writerow([])

        # Analytical Breakdowns
        writer.writerow(["--- ANALYTICAL BREAKDOWNS ---"])
        writer.writerow(["Section", "Category", "Value"])
        for sec in evidence.get("sections", []):
            if sec.get("section_type") == "chart":
                for item in sec.get("chart_items", []):
                    writer.writerow([sec.get("title"), item.get("label"), item.get("value")])
        writer.writerow([])

        # Tabular Data Section
        for sec in evidence.get("sections", []):
            if sec.get("section_type") == "table":
                cols = sec.get("columns", [])
                rows = sec.get("rows", [])
                if cols and rows:
                    writer.writerow([f"--- TABLE: {sec.get('title')} ---"])
                    writer.writerow(cols)
                    for r in rows:
                        writer.writerow([r.get(c, "") for c in cols])
                    writer.writerow([])

        # Data Lineage
        writer.writerow(["--- DATA PROVENANCE ---"])
        writer.writerow(["Dataset Name", "Dataset ID", "Version ID", "Total Records", "Manifest Hash"])
        for p in evidence.get("provenance", []):
            writer.writerow([
                p.get("dataset_name"),
                p.get("dataset_id"),
                p.get("version_id"),
                p.get("row_count"),
                p.get("manifest_sha256"),
            ])

        return buf.getvalue().encode("utf-8")
