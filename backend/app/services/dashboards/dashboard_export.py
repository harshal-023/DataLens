import csv
import io
from datetime import UTC, datetime
from typing import Any

import openpyxl
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


def export_dashboard_pdf(
    dashboard_title: str,
    workspace_name: str,
    description: str | None,
    widget_results: list[dict[str, Any]],
    applied_filters: list[dict[str, Any]] | None = None,
) -> bytes:
    """
    Generates a high-quality PDF dashboard report conforming strictly to the DataLens
    Deep Navy & Peacock Teal visual identity.
    """
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
    teal = colors.HexColor("#009F98")
    deep_navy = colors.HexColor("#102C46")
    cool_grey = colors.HexColor("#52616C")
    light_bg = colors.HexColor("#F5F8FA")

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
        fontSize=9,
        leading=12,
        textColor=cool_grey,
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=deep_navy,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=deep_navy,
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph(f"DataLens Dashboard — {dashboard_title}", title_style))
    elements.append(Spacer(1, 4))
    elements.append(
        Paragraph(
            f"Workspace: <b>{workspace_name}</b> | Exported: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle_style,
        )
    )
    if description:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(description, subtitle_style))

    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=2, color=teal, spaceBefore=4, spaceAfter=12))

    # Applied Filters Summary
    if applied_filters:
        elements.append(Paragraph("Active Dashboard Filters", h2_style))
        filter_rows = [["Filter", "Column", "Condition"]]
        for f in applied_filters:
            filter_rows.append([
                str(f.get("name", "Filter")),
                str(f.get("column", "-")),
                f"{f.get('operator', 'eq')}: {f.get('value', '')}",
            ])
        t_filters = Table(filter_rows, colWidths=[140, 140, 260])
        t_filters.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
            ])
        )
        elements.append(t_filters)
        elements.append(Spacer(1, 12))

    # Widgets Summary
    elements.append(Paragraph("Dashboard Widgets & Visualizations", h2_style))

    for w_idx, res in enumerate(widget_results, 1):
        w_title = res.get("title", f"Widget #{w_idx}")
        w_type = res.get("widget_type", "metric").upper()
        data = res.get("data", {})

        elements.append(Paragraph(f"{w_idx}. {w_title} ({w_type})", h2_style))

        if w_type in ("KPI", "GAUGE"):
            val = data.get("formatted_value", str(data.get("value", "0")))
            metric = data.get("metric", "Metric")
            rows = [[metric, val]]
            if data.get("comparison"):
                comp = data["comparison"]
                rows.append(["Comparison (Target)", f"{comp.get('target', 0)} ({comp.get('pct_change', 0)}% {comp.get('direction', '')})"])
            elif data.get("target"):
                rows.append(["Target", f"{data.get('target', 0)} ({data.get('percent_of_target', 0)}% of target)"])
            kpi_table = Table(rows, colWidths=[200, 340])
            kpi_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (0, 0), 10),
                    ("FONTSIZE", (1, 0), (1, 0), 16),
                    ("TEXTCOLOR", (1, 0), (1, 0), teal),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                ])
            )
            elements.append(kpi_table)

        elif w_type in ("BAR", "PIE", "DONUT", "HORIZONTAL_BAR", "TOP_N", "FUNNEL", "WATERFALL", "PARETO"):
            items = data.get("items") or data.get("stages") or []
            items = items[:10]  # top 10 in PDF
            if items:
                table_data = [["Dimension / Stage", "Value"]]
                for item in items:
                    v = item.get("value", 0)
                    formatted_v = f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)
                    lbl = item.get("label") or item.get("name") or ""
                    table_data.append([str(lbl), formatted_v])

                t = Table(table_data, colWidths=[270, 270])
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                    ])
                )
                elements.append(t)
            else:
                elements.append(Paragraph("<i>No data returned.</i>", subtitle_style))

        elif w_type in ("STACKED_BAR", "GROUPED_BAR", "PERCENT_BAR"):
            cats = data.get("categories", [])[:8]
            series_list = data.get("series", [])[:4]
            if cats and series_list:
                headers = ["Category"] + [s.get("name", "Series") for s in series_list]
                table_data = [headers]
                col_w = max(40, 540 // len(headers))
                for c_idx, cat in enumerate(cats):
                    r_vals = [cat] + [f"{s['values'][c_idx]:,.1f}" if c_idx < len(s['values']) else "0" for s in series_list]
                    table_data.append(r_vals)
                t = Table(table_data, colWidths=[col_w] * len(headers))
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                    ])
                )
                elements.append(t)
            else:
                elements.append(Paragraph("<i>No data returned.</i>", subtitle_style))

        elif w_type in ("LINE", "AREA", "MULTI_LINE", "STACKED_AREA", "COMBO"):
            pts = data.get("points") or []
            if pts:
                table_data = [["Timestamp", "Metric Value"]]
                for p in pts[:12]:
                    v = p.get("value", 0)
                    formatted_v = f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)
                    table_data.append([str(p.get("timestamp", "")), formatted_v])

                t = Table(table_data, colWidths=[270, 270])
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                    ])
                )
                elements.append(t)
            elif data.get("labels") and data.get("series"):
                labels = data.get("labels", [])[:8]
                s_list = data.get("series", [])[:3]
                headers = ["Time"] + [s.get("name", "Series") for s in s_list]
                table_data = [headers]
                col_w = max(40, 540 // len(headers))
                for l_idx, lbl in enumerate(labels):
                    r_vals = [lbl] + [f"{s['values'][l_idx]:,.1f}" if l_idx < len(s['values']) else "0" for s in s_list]
                    table_data.append(r_vals)
                t = Table(table_data, colWidths=[col_w] * len(headers))
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                    ])
                )
                elements.append(t)
            else:
                elements.append(Paragraph("<i>No time-series points returned.</i>", subtitle_style))

        elif w_type == "HISTOGRAM":
            bins = data.get("bins", [])[:10]
            if bins:
                table_data = [["Range / Bucket", "Frequency Count"]]
                for b in bins:
                    table_data.append([str(b.get("label", "")), str(b.get("count", 0))])
                t = Table(table_data, colWidths=[270, 270])
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                    ])
                )
                elements.append(t)

        elif w_type == "BOX_PLOT":
            items = data.get("items", [])[:8]
            if items:
                table_data = [["Category", "Min", "Q1", "Median", "Q3", "Max"]]
                for it in items:
                    table_data.append([
                        str(it.get("label", "")),
                        str(it.get("min", 0)),
                        str(it.get("q1", 0)),
                        str(it.get("median", 0)),
                        str(it.get("q3", 0)),
                        str(it.get("max", 0)),
                    ])
                t = Table(table_data, colWidths=[140, 80, 80, 80, 80, 80])
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                    ])
                )
                elements.append(t)

        elif w_type == "TEXT":
            content = data.get("content", "")
            elements.append(Paragraph(content or "<i>Empty text widget</i>", body_style))

        elif w_type == "TABLE":
            cols = data.get("columns", [])[:6]
            rows = data.get("rows", [])[:10]
            if cols and rows:
                col_w = max(40, 540 // len(cols))
                table_data = [cols]
                for r in rows:
                    table_data.append([str(r.get(c, "")) for c in cols])
                t = Table(table_data, colWidths=[col_w] * len(cols))
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), deep_navy),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE5EB")),
                    ])
                )
                elements.append(t)

        elements.append(Spacer(1, 10))

    doc.build(elements)
    return buffer.getvalue()


def export_dashboard_xlsx(
    dashboard_title: str,
    workspace_name: str,
    widget_results: list[dict[str, Any]],
) -> bytes:
    wb = openpyxl.Workbook()
    navy_fill = PatternFill(start_color="102C46", end_color="102C46", fill_type="solid")
    teal_fill = PatternFill(start_color="009F98", end_color="009F98", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=15, bold=True, color="102C46")

    # Cover Sheet
    ws_cover = wb.active
    ws_cover.title = "Dashboard Summary"
    ws_cover.append([dashboard_title])
    ws_cover["A1"].font = title_font
    ws_cover.append([f"Workspace: {workspace_name} | Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}"])
    ws_cover.append([])
    ws_cover.append(["Widget Title", "Type", "Status / Records"])
    for cell in ws_cover[4]:
        cell.fill = navy_fill
        cell.font = header_font

    for res in widget_results:
        w_title = res.get("title", "Widget")
        w_type = res.get("widget_type", "metric")
        rows = res.get("row_count", 0)
        ws_cover.append([w_title, w_type, f"{rows} rows computed"])

    # Additional sheets per widget with tabular or categorical data
    for idx, res in enumerate(widget_results, 1):
        w_title = res.get("title", f"Widget_{idx}")
        safe_sheet_name = "".join(c for c in w_title if c.isalnum() or c in (" ", "_"))[:25] or f"Widget_{idx}"
        w_type = res.get("widget_type", "").lower()
        data = res.get("data", {})

        if w_type in ("bar", "pie", "donut", "horizontal_bar", "top_n", "funnel", "waterfall", "pareto"):
            items = data.get("items") or data.get("stages") or []
            if items:
                ws = wb.create_sheet(title=safe_sheet_name)
                ws.append(["Dimension / Category", "Value"])
                for cell in ws[1]:
                    cell.fill = teal_fill
                    cell.font = header_font
                for it in items:
                    lbl = it.get("label") or it.get("name") or ""
                    ws.append([lbl, it.get("value", 0)])

        elif w_type in ("stacked_bar", "grouped_bar", "percent_bar"):
            cats = data.get("categories", [])
            series_list = data.get("series", [])
            if cats and series_list:
                ws = wb.create_sheet(title=safe_sheet_name)
                headers = ["Category"] + [s.get("name", "Series") for s in series_list]
                ws.append(headers)
                for cell in ws[1]:
                    cell.fill = teal_fill
                    cell.font = header_font
                for c_idx, cat in enumerate(cats):
                    r_vals = [cat] + [s["values"][c_idx] if c_idx < len(s["values"]) else 0 for s in series_list]
                    ws.append(r_vals)

        elif w_type in ("line", "area", "multi_line", "stacked_area", "combo"):
            pts = data.get("points", [])
            if pts:
                ws = wb.create_sheet(title=safe_sheet_name)
                ws.append(["Timestamp", "Value"])
                for cell in ws[1]:
                    cell.fill = teal_fill
                    cell.font = header_font
                for pt in pts:
                    ws.append([pt.get("timestamp", ""), pt.get("value", 0)])
            elif data.get("labels") and data.get("series"):
                labels = data.get("labels", [])
                s_list = data.get("series", [])
                ws = wb.create_sheet(title=safe_sheet_name)
                headers = ["Time"] + [s.get("name", "Series") for s in s_list]
                ws.append(headers)
                for cell in ws[1]:
                    cell.fill = teal_fill
                    cell.font = header_font
                for l_idx, lbl in enumerate(labels):
                    r_vals = [lbl] + [s["values"][l_idx] if l_idx < len(s["values"]) else 0 for s in s_list]
                    ws.append(r_vals)

        elif w_type == "table":
            cols = data.get("columns", [])
            table_rows = data.get("rows", [])
            if cols and table_rows:
                ws = wb.create_sheet(title=safe_sheet_name)
                ws.append(cols)
                for cell in ws[1]:
                    cell.fill = teal_fill
                    cell.font = header_font
                for r in table_rows:
                    ws.append([r.get(c, "") for c in cols])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_dashboard_csv(
    dashboard_title: str,
    widget_results: list[dict[str, Any]],
) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["# DataLens Dashboard Export", dashboard_title])
    writer.writerow(["# Generated At", datetime.now(UTC).isoformat()])
    writer.writerow([])

    for res in widget_results:
        w_title = res.get("title", "Widget")
        w_type = res.get("widget_type", "").lower()
        data = res.get("data", {})

        writer.writerow([f"=== WIDGET: {w_title} ({w_type.upper()}) ==="])

        if w_type in ("kpi", "gauge"):
            writer.writerow(["Metric", "Value"])
            writer.writerow([data.get("metric", "Value"), data.get("value", 0)])
        elif w_type in ("bar", "pie", "donut", "horizontal_bar", "top_n", "funnel", "waterfall", "pareto"):
            writer.writerow(["Category", "Value"])
            items = data.get("items") or data.get("stages") or []
            for it in items:
                lbl = it.get("label") or it.get("name") or ""
                writer.writerow([lbl, it.get("value", 0)])
        elif w_type in ("stacked_bar", "grouped_bar", "percent_bar"):
            cats = data.get("categories", [])
            series_list = data.get("series", [])
            headers = ["Category"] + [s.get("name", "Series") for s in series_list]
            writer.writerow(headers)
            for c_idx, cat in enumerate(cats):
                r_vals = [cat] + [s["values"][c_idx] if c_idx < len(s["values"]) else 0 for s in series_list]
                writer.writerow(r_vals)
        elif w_type in ("line", "area", "multi_line", "stacked_area", "combo"):
            pts = data.get("points") or []
            if pts:
                writer.writerow(["Timestamp", "Value"])
                for pt in pts:
                    writer.writerow([pt.get("timestamp", ""), pt.get("value", 0)])
            elif data.get("labels") and data.get("series"):
                labels = data.get("labels", [])
                s_list = data.get("series", [])
                headers = ["Time"] + [s.get("name", "Series") for s in s_list]
                writer.writerow(headers)
                for l_idx, lbl in enumerate(labels):
                    r_vals = [lbl] + [s["values"][l_idx] if l_idx < len(s["values"]) else 0 for s in s_list]
                    writer.writerow(r_vals)
        elif w_type == "table":
            cols = data.get("columns", [])
            writer.writerow(cols)
            for r in data.get("rows", []):
                writer.writerow([r.get(c, "") for c in cols])
        writer.writerow([])

    return output.getvalue().encode("utf-8")

