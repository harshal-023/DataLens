import io
from datetime import datetime
from typing import Any

import docx
from docx.shared import Inches, Pt, RGBColor


def generate_docx_report(
    title: str,
    dataset_name: str,
    version_number: str,
    workspace_name: str,
    profile_data: dict[str, Any] | None = None,
    stats_data: dict[str, Any] | None = None,
    agg_data: dict[str, Any] | None = None,
    quality_data: dict[str, Any] | None = None,
) -> bytes:
    doc = docx.Document()

    # Set Margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    # Document Title
    h1 = doc.add_heading(title, level=0)
    h1.runs[0].font.color.rgb = RGBColor(16, 44, 70)  # #102C46 Deep Navy
    h1.runs[0].font.size = Pt(22)

    # Subtitle / Metadata
    gen_time = datetime.now().strftime("%d %b %Y, %H:%M UTC")
    meta_p = doc.add_paragraph()
    meta_p.add_run(f"Dataset: {dataset_name}  |  Version: {version_number}  |  Workspace: {workspace_name}  |  Generated: {gen_time}").italic = True

    # 1. Executive Summary
    h2 = doc.add_heading("1. Executive Summary & Core KPIs", level=1)
    h2.runs[0].font.color.rgb = RGBColor(0, 159, 152)  # #009F98 Teal

    row_count = profile_data.get("row_count", 0) if profile_data else 0
    col_count = profile_data.get("column_count", 0) if profile_data else 0
    q_score = quality_data.get("quality_score", 95) if quality_data else 95

    kpi_p = doc.add_paragraph()
    kpi_p.add_run(f"• Total Analyzed Records: {row_count:,}\n").bold = True
    kpi_p.add_run(f"• Dimension & Metric Columns: {col_count}\n").bold = True
    kpi_p.add_run(f"• Overall Data Quality Score: {q_score}/100\n").bold = True

    # 2. Descriptive Statistics Table
    if stats_data and stats_data.get("columns"):
        h_stats = doc.add_heading("2. Column Descriptive Statistics", level=1)
        h_stats.runs[0].font.color.rgb = RGBColor(0, 159, 152)

        stats_cols = [c for c, s in stats_data["columns"].items() if s.get("sum") is not None]
        if stats_cols:
            table = doc.add_table(rows=1, cols=6)
            table.style = "Table Grid"
            hdr_cells = table.rows[0].cells
            headers = ["Column", "Sum", "Mean", "Median", "Min", "Max"]
            for i, h in enumerate(headers):
                hdr_cells[i].text = h
                hdr_cells[i].paragraphs[0].runs[0].bold = True

            for col_name in stats_cols[:15]:
                cs = stats_data["columns"][col_name]
                row_cells = table.add_row().cells
                row_cells[0].text = col_name
                row_cells[1].text = f"{cs.get('sum', 0):,}"
                row_cells[2].text = f"{cs.get('mean', 0):,}"
                row_cells[3].text = f"{cs.get('median', 0):,}"
                row_cells[4].text = f"{cs.get('min', 0):,}"
                row_cells[5].text = f"{cs.get('max', 0):,}"

    # 3. Aggregation Breakdown
    if agg_data and agg_data.get("items"):
        doc.add_paragraph()
        h_agg = doc.add_heading(
            f"3. Aggregated Metrics: {agg_data.get('aggregation', '').upper()}({agg_data.get('metric_column')}) by {', '.join(agg_data.get('group_by_columns', []))}",
            level=1,
        )
        h_agg.runs[0].font.color.rgb = RGBColor(0, 159, 152)

        table_agg = doc.add_table(rows=1, cols=4)
        table_agg.style = "Table Grid"
        hdr_agg = table_agg.rows[0].cells
        hdr_agg[0].text = "Group Key"
        hdr_agg[1].text = "Aggregated Value"
        hdr_agg[2].text = "Row Count"
        hdr_agg[3].text = "Share of Total"
        for c in hdr_agg:
            c.paragraphs[0].runs[0].bold = True

        for item in agg_data["items"][:20]:
            r_cells = table_agg.add_row().cells
            r_cells[0].text = str(item.get("key", ""))
            r_cells[1].text = item.get("formatted_value") or f"{item.get('value', 0):,}"
            r_cells[2].text = f"{item.get('count', 0):,}"
            r_cells[3].text = f"{item.get('share_of_total', 0)}%"

    # 4. Data Quality Findings
    if quality_data and quality_data.get("issues"):
        doc.add_paragraph()
        h_q = doc.add_heading("4. Data Quality Audit & Recommendations", level=1)
        h_q.runs[0].font.color.rgb = RGBColor(0, 159, 152)

        for iss in quality_data["issues"]:
            p = doc.add_paragraph()
            p.add_run(f"[{iss.get('severity', 'info').upper()}] {iss.get('title')}: ").bold = True
            p.add_run(f"{iss.get('description')} ")
            if iss.get("suggested_action"):
                p.add_run(f"Recommendation: {iss.get('suggested_action')}").italic = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

