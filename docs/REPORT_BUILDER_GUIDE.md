# DataLens — Report Builder Guide

## Overview

The DataLens Report Builder provides an interactive, stepper-based workflow for authoring executive and departmental business reports grounded in immutable datasets, live dashboards, and predictive model runs.

---

## 1. Navigating to the Report Builder

- Open **Reports** from the main navigation sidebar (`/reports`).
- Click **"Create Report"** or select any card in the **"Predefined Business Templates"** gallery to launch with pre-configured settings.
- The Report Builder is hosted at `/reports/new`.

---

## 2. Stepper Workflow

The builder guides users through four streamlined steps:

```
[1. Select Template] ───► [2. Report Metadata] ───► [3. Section Layout] ───► [4. Preview & Save]
```

### Step 1: Template Selection
Select from 8 professional predefined templates:
- **Executive Business Review**: High-level strategic briefing with KPIs, narratives, and risk outlook.
- **Sales Performance Report**: Revenue, conversion pipelines, regional targets, and quota attainment.
- **Financial Performance Report**: Margins, EBITDA, cash flow, OPEX variance, and fiscal health.
- **Marketing Analytics Summary**: CAC, ROAS, channel attribution, conversion funnels, and LTV.
- **Customer & Retention Analysis**: Cohorts, churn rate, Net Retention Rate (NRR), and satisfaction.
- **Operations & Fulfillment Review**: Lead times, SLA adherence, unit costs, and inventory turns.
- **Predictive & ML Forecast Report**: Supervised forecasting, feature importance, and cluster segments.
- **Custom Modular Report**: Fully configurable blank canvas for ad-hoc business needs.

### Step 2: Metadata & Data Scope
Define the essential parameters and data source connections:
- **Report Title & Subtitle**: Clear business title and contextual subtitle.
- **Audience & Department**: Target stakeholders (Executive Board, Department Leads, Investors, Leadership).
- **Target Period**: Reporting interval (e.g., `Q3 2026`, `FY 2026`, `Monthly - Oct 2026`).
- **Primary Dataset**: Bound Parquet dataset providing the underlying metrics.
- **Linked Dashboard (Optional)**: Seamlessly pull widgets and interactive charts directly from Phase 4A/4C dashboards.
- **Branding Theme**: Choose from `Navy & Teal` (DataLens default), `Monochrome Slate`, `Emerald Corporate`, or `Indigo Modern`.

### Step 3: Section Configuration
Toggle and customize the sections included in the final report:
- **Cover Page**: Professional cover with title, period, department badge, author, and timestamp.
- **Executive Summary**: High-level narrative synthesized deterministically or with Gemini AI grounding.
- **Key Performance Indicators (KPIs)**: Metric cards with values, targets, deltas, and trend badges.
- **Visual Analytics**: Interactive charts and breakdowns imported from dashboards or generated from DuckDB aggregates.
- **Key Findings & Drivers**: Bulleted analytical observations explaining underlying variance.
- **Actionable Recommendations**: Strategic priorities, next steps, and owner assignments.
- **Data Provenance & Audit Trail**: Cryptographic SHA-256 hash, dataset version ID, row count, and generation timestamp.

### Step 4: Preview & Save
- Review the generated layout structure.
- Save as **Draft** or **Publish** immediately to the Reports Library.
- Run instant ad-hoc generation or configure an automated recurring schedule.

---

## 3. Editing and Managing Existing Reports

- From the **Reports Library** (`/reports`), click on any report card to open the **Report Preview** (`/reports/:reportId`).
- Use the action bar to:
  - **Run Now**: Trigger an on-demand report execution.
  - **Export**: Instantly download in PDF, DOCX, XLSX, or CSV formats.
  - **Schedule**: Configure automated daily, weekly, or monthly runs.
  - **History**: View all past runs, duration, and download previous output files at `/reports/:reportId/history`.

