import io
from datetime import datetime
from typing import Any

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


def generate_pdf_report(
    title: str,
    dataset_name: str,
    version_number: str,
    workspace_name: str,
    profile_data: dict[str, Any] | None = None,
    stats_data: dict[str, Any] | None = None,
    agg_data: dict[str, Any] | None = None,
    quality_data: dict[str, Any] | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Brand Colors: Peacock Teal #009F98, Deep Navy #102C46, Cool Grey #52616C
    teal = colors.HexColor("#009F98")
    deep_navy = colors.HexColor("#102C46")
    cool_grey = colors.HexColor("#52616C")
    light_bg = colors.HexColor("#F5F8FA")
    accent_bg = colors.HexColor("#EDF7FA")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=deep_navy,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=cool_grey,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=deep_navy,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=deep_navy,
    )
    header_cell_style = ParagraphStyle(
        "HeaderCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.white,
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 4))
    gen_time = datetime.now().strftime("%d %b %Y, %H:%M UTC")
    meta_text = (
        f"<b>Dataset:</b> {dataset_name} &nbsp;|&nbsp; <b>Version:</b> {version_number} &nbsp;|&nbsp; "
        f"<b>Workspace:</b> {workspace_name} &nbsp;|&nbsp; <b>Generated:</b> {gen_time}"
    )
    story.append(Paragraph(meta_text, subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=teal, spaceAfter=15))

    # 2. Executive Summary Metrics Grid
    story.append(Paragraph("Executive Summary & High-Level KPIs", heading_style))
    story.append(Spacer(1, 6))

    row_count = profile_data.get("row_count", 0) if profile_data else 0
    col_count = profile_data.get("column_count", 0) if profile_data else 0
    q_score = quality_data.get("quality_score", 95) if quality_data else 95

    kpi_data = [
        [
            Paragraph("<b>Total Verified Records</b>", subtitle_style),
            Paragraph("<b>Columns</b>", subtitle_style),
            Paragraph("<b>Data Quality Health</b>", subtitle_style),
        ],
        [
            Paragraph(f"<font size=14 color='#009F98'><b>{row_count:,}</b></font>", heading_style),
            Paragraph(f"<font size=14 color='#102C46'><b>{col_count}</b></font>", heading_style),
            Paragraph(f"<font size=14 color='#216548'><b>{q_score}/100</b></font>", heading_style),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[180, 180, 180])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), accent_bg),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BBDCE8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 15))

    # 3. Descriptive Statistics Table
    if stats_data and stats_data.get("columns"):
        story.append(Paragraph("Descriptive Column Statistics", heading_style))
        story.append(Spacer(1, 6))

        stats_table_data = [
            [
                Paragraph("Column", header_cell_style),
                Paragraph("Sum", header_cell_style),
                Paragraph("Mean", header_cell_style),
                Paragraph("Median", header_cell_style),
                Paragraph("Min", header_cell_style),
                Paragraph("Max", header_cell_style),
                Paragraph("Std Dev", header_cell_style),
            ]
        ]

        for col_name, c_stats in list(stats_data["columns"].items())[:12]:
            if c_stats.get("sum") is not None:
                stats_table_data.append(
                    [
                        Paragraph(col_name, cell_style),
                        Paragraph(f"{c_stats.get('sum', 0):,}", cell_style),
                        Paragraph(f"{c_stats.get('mean', 0):,}", cell_style),
                        Paragraph(f"{c_stats.get('median', 0):,}", cell_style),
                        Paragraph(f"{c_stats.get('min', 0):,}", cell_style),
                        Paragraph(f"{c_stats.get('max', 0):,}", cell_style),
                        Paragraph(f"{c_stats.get('standard_deviation', 0):,}", cell_style),
                    ]
                )

        if len(stats_table_data) > 1:
            st_table = Table(stats_table_data, colWidths=[90, 75, 75, 75, 75, 75, 75])
            st_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                        ("PADDING", (0, 0), (-1, -1), 4),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                    ]
                )
            )
            story.append(st_table)
            story.append(Spacer(1, 15))

    # 4. Aggregated Breakdown
    if agg_data and agg_data.get("items"):
        story.append(
            Paragraph(
                f"Aggregated Breakdown: {agg_data.get('aggregation', '').upper()}({agg_data.get('metric_column')}) by {', '.join(agg_data.get('group_by_columns', []))}",
                heading_style,
            )
        )
        story.append(Spacer(1, 6))

        agg_table_data = [
            [
                Paragraph("Group", header_cell_style),
                Paragraph("Metric Value", header_cell_style),
                Paragraph("Row Count", header_cell_style),
                Paragraph("Share of Total", header_cell_style),
            ]
        ]

        for item in agg_data["items"][:15]:
            agg_table_data.append(
                [
                    Paragraph(item.get("key", ""), cell_style),
                    Paragraph(item.get("formatted_value") or f"{item.get('value', 0):,}", cell_style),
                    Paragraph(f"{item.get('count', 0):,}", cell_style),
                    Paragraph(f"{item.get('share_of_total', 0)}%", cell_style),
                ]
            )

        ag_table = Table(agg_table_data, colWidths=[180, 120, 120, 120])
        ag_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), teal),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                ]
            )
        )
        story.append(ag_table)
        story.append(Spacer(1, 15))

    # 5. Data Quality Findings
    if quality_data and quality_data.get("issues"):
        story.append(Paragraph("Data Quality Findings & Remediation", heading_style))
        story.append(Spacer(1, 6))

        q_table_data = [
            [
                Paragraph("Severity", header_cell_style),
                Paragraph("Issue", header_cell_style),
                Paragraph("Affected Count", header_cell_style),
                Paragraph("Recommendation", header_cell_style),
            ]
        ]

        for iss in quality_data["issues"][:8]:
            sev = iss.get("severity", "info").upper()
            q_table_data.append(
                [
                    Paragraph(f"<b>{sev}</b>", cell_style),
                    Paragraph(iss.get("title", ""), cell_style),
                    Paragraph(f"{iss.get('affected_count', 0):,}", cell_style),
                    Paragraph(iss.get("suggested_action", ""), cell_style),
                ]
            )

        qt_table = Table(q_table_data, colWidths=[70, 160, 90, 220])
        qt_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B3A42")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                ]
            )
        )
        story.append(qt_table)
        story.append(Spacer(1, 15))

    # Build PDF
    doc.build(story)
    return buffer.getvalue()

