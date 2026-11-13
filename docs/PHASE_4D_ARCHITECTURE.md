# DataLens — Phase 4D Architecture Specification
# Automated Business Reporting & Report Generation Engine

## 1. Overview & Objectives

Phase 4D is the culmination of Phase 4 in DataLens. It introduces a comprehensive, enterprise-grade Automated Business Reporting system that enables users to:
1. Define and customize multi-section **Business Reports** with modular data sources (DuckDB analytics, interactive dashboards, advanced visualizations, data transformation lineage, and ML model runs).
2. Utilize professional **Predefined Templates** (Executive Business Review, Sales Performance, Financial Performance, Marketing Analytics, Customer Analytics, Operations, Predictive Analytics, and Custom).
3. Generate high-fidelity **Multi-Format Exports** (PDF with ReportLab cover pages & styling, editable Microsoft Word DOCX, structured Microsoft Excel XLSX with multiple tabs, and standard CSV).
4. Integrate **Gemini AI Narratives** (executive summaries, KPI explanations, business findings, actionable recommendations) grounded strictly in verified evidence, with guaranteed **deterministic template fallback** when AI is unavailable.
5. Automate recurring report generation with **Flexible Schedules** (Daily, Weekly, Monthly) supporting user timezones, next-run calculations, concurrency locks, and failure tracking.
6. Support secure **Email Delivery** with backend credential management, attachment handling, size checks, recipient authorization, and delivery audit logs.
7. Provide a responsive **Report Builder & Management UI** matching DataLens design identity (Deep Navy `#102C46`, Peacock Teal `#009F98`, Light Teal `#39C3B8`).

---

## 2. Existing Infrastructure & Reusability Audit

### 2.1 Backend Analytical & Export Engines
- **DuckDB Analytics (`app.services.analytics.engine.AnalyticsEngine`)**:
  - Provides zero-fabrication aggregation, descriptive statistics, correlation, quantile, and Pareto computations directly from immutable Parquet datasets.
- **Interactive Dashboards (`app.services.dashboards.dashboard_service.DashboardService`)**:
  - Provides widget definitions, queries, and filters across 20+ chart types from Phase 4A & 4C.
- **Machine Learning Registry (`app.services.ml.service.MLService`, `ModelRun`)**:
  - Contains forecasts (moving average, exponential smoothing, linear trend), anomaly detection (z-score, IQR, isolation forest), and segmentation (k-means) model run metadata.
- **Data Transformation Engine (`app.services.transformation.service.TransformationService`)**:
  - Contains pipeline lineage, step executions, and derived dataset IDs.
- **AI / LLM Integration (`app.services.ai.gemini_provider.GeminiProvider`, `factory.py`)**:
  - Google Gemini API abstraction (`gemini-1.5-flash`, `gemini-1.5-pro`) for high-fidelity text generation with JSON / structured markdown modes.
- **Document Generation Libraries**:
  - `reportlab`: Custom canvas, styles, tables, colors for PDF generation.
  - `python-docx`: Document, headings, tables, cell shading for DOCX.
  - `openpyxl`: Multi-tab workbook creation, font styles, column auto-width for XLSX.
  - Python standard `csv`: Streaming CSV output.

### 2.2 Database & Persistence Strategy
Existing `reports` table stores single dataset exports from Phase 1/2. For Phase 4D, we establish a robust relational schema:
1. `report_templates`: Reusable template blueprints with predefined section configurations.
2. `business_reports`: Core persistent report definition containing section list, filters, bound dashboards, datasets, and ML runs.
3. `report_runs`: Immutable historical execution records capturing execution status, period, provenance evidence, generated file metadata, execution latency, and error logs.
4. `report_schedules`: Cron/interval schedule configuration with frequency, timezone, next run time, email delivery recipients, and enabled flag.

---

## 3. Data Models & Relational Architecture

```
                          ┌────────────────────────┐
                          │       Workspaces       │
                          └───────────┬────────────┘
                                      │ 1
                                      ▼ *
┌───────────────────────┐      ┌────────────────────────┐      ┌───────────────────────┐
│    ReportTemplates    │◄────┤     BusinessReports    ├─────►│    ReportSchedules    │
│  (Config & Sections)  │  1   │  (Sections & Bindings) │  1   │  (Cron, TZ, Delivery) │
└───────────────────────┘      └───────────┬────────────┘      └───────────────────────┘
                                           │ 1
                                           ▼ *
                               ┌────────────────────────┐
                               │       ReportRuns       │
                               │  (History, Provenance, │
                               │   Files, Status, Error)│
                               └────────────────────────┘
```

---

## 4. Deterministic Assembly Engine & Provenance

To satisfy DataLens's analytical integrity guarantees:
1. **Report Evidence Collector**:
   - Compiles exact execution results from specified dataset versions, dashboard widgets, and ML model runs.
   - Attaches strict provenance metadata: `{ dataset_id, version_id, source_query, row_count, timestamp }`.
2. **Gemini AI Grounding**:
   - Gemini only receives aggregated summary metrics and statistical facts (never raw dataset cells).
   - Prompts strictly instruct the model to produce evidence-backed findings and recommendations without fabricating metrics.
   - If Gemini is disabled or fails, the report engine invokes deterministic rule-based template generation.
3. **Multi-Format Generation**:
   - PDF, DOCX, XLSX, and CSV generators consume the identical evidence object ensuring 100% format parity.

---

## 5. Scheduling & Email Delivery Engine

- **Persistent Scheduler**: Evaluates `report_schedules` records whose `next_run_at <= now() AND is_enabled = true`.
- **Concurrency & Idempotency**: Atomic row locking or timestamp advancement avoids duplicate triggers.
- **Email Delivery Service**: Sends notification emails with attachments or download links to authorized recipients, logging status to `report_runs`.

