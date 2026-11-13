# DataLens — Automated Report Generation Architecture

## Overview

The DataLens Automated Report Generation Engine orchestrates data assembly, AI-grounded narrative synthesis, multi-format rendering, and file archiving into an immutable, verifiable business report pipeline.

---

## 1. End-to-End Generation Pipeline

```
  ┌────────────────────────────────────────────────────────┐
  │                 Trigger (Ad-Hoc / Schedule)            │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │              1. ReportAssemblyService                  │
  │  - Fetch Immutable Parquet Dataset Metadata & SHA-256  │
  │  - Execute DuckDB Aggregations (KPIs, Trends)         │
  │  - Query Linked Dashboard Widgets & Visuals            │
  │  - Pull ML Model Run Registry Metrics (if applicable)  │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │         2. GeminiReportWriter & Fallback Engine        │
  │  - Construct Structured Evidence Payload               │
  │  - Synthesize Executive Summary & Risk Factors         │
  │  - Fallback: Strict Deterministic Narrative Engine     │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │         3. Multi-Format Rendering Engine               │
  │  - PDF: ReportLab (Cover, Tables, Metric Cards, Charts)│
  │  - DOCX: python-docx (Formatted Headings, Highlights)  │
  │  - XLSX: openpyxl (Summary, KPIs, Breakdown Sheets)    │
  │  - CSV: Tabular Data with Provenance Metadata Header   │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │          4. ReportRun Record & File Storage            │
  │  - Persist to Local Storage Root (local_storage/reports)│
  │  - Record Execution Duration, Status, File Size & SHA  │
  │  - Trigger Email Delivery (if recipients configured)   │
  └────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Format Output Generation

### PDF Export (`business_report_export.generate_pdf_report`)
- Powered by `reportlab`.
- Generates publication-ready documents formatted according to DataLens branding:
  - Deep Navy `#102C46` headers and cover elements.
  - Peacock Teal `#009F98` accent lines, section rules, and KPI badges.
  - Summary tables with alternate row shading (`#F8FAFC`).
  - Cryptographic provenance footer on every page.

### DOCX Export (`business_report_export.generate_docx_report`)
- Powered by `python-docx`.
- Generates editable Word documents with native styles:
  - Title & Subtitle styled with organizational branding.
  - Formatted tables with header styling and cell padding.
  - Bulleted recommendations and analytical findings.
  - Metadata block recording generator, dataset version, and generation timestamp.

### XLSX Export (`business_report_export.generate_xlsx_report`)
- Powered by `openpyxl`.
- Multi-tab workbook structure:
  - **Tab 1: Summary**: Report metadata, audience, period, and executive narrative.
  - **Tab 2: KPIs**: Metric names, values, targets, percentage changes, and status.
  - **Tab 3: Breakdowns**: Segment analysis, categorical distributions, and time trends.
  - **Tab 4: Provenance**: Dataset ID, Parquet version, SHA-256 hash, and row counts.

### CSV Export (`business_report_export.generate_csv_report`)
- Standard RFC 4180 CSV generation with contextual metadata header lines:
  - Line 1-5: Metadata prefixed with `#` (Title, Period, Generated At, SHA-256).
  - Subsequent lines: Rectangular tabular breakdown data.

---

## 3. Gemini AI Grounding & Strict Deterministic Fallback

To prevent LLM hallucination and guarantee 100% data fidelity:
1. **Zero Raw Cell Upload**: Only calculated mathematical aggregations (e.g., sum, mean, standard deviation, min, max, delta percentages) are passed to the narrative prompt.
2. **Grounding Constraints**: Gemini is strictly prompted to reference only the provided numbers. Speculation beyond the verified statistical context is forbidden.
3. **Deterministic Fallback Engine (`deterministic_narrative.py`)**:
   - If `GEMINI_API_KEY` is absent, disabled, or an API error occurs, DataLens automatically switches to pure deterministic template synthesis.
   - Formats summary statements, metric highlights, and directional findings using rule-based algorithmic logic.
   - The report generation **never fails** due to AI unavailability.

