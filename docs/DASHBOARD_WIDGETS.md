# DataLens — Dashboard Widgets & Visualization Engine

## Overview

DataLens dashboards support nine distinct widget types designed to address executive summaries, statistical trends, categorical distributions, correlations, and raw data inspection.

Every calculation is executed directly in DuckDB against immutable Parquet data files. The system never fabricates or hallucinates numbers.

---

## Supported Widget Types

### 1. KPI Card (`kpi`)
- **Purpose:** Highlights primary performance metrics (e.g. Total Revenue, Customer Count, Average Order Value).
- **DuckDB Operation:** Global aggregate query `SELECT {AGG}({metric_column}) FROM {parquet}`.
- **Aggregations:** `sum`, `avg`, `count`, `min`, `max`, `distinct_count`.
- **Features:** Unit prefix/suffix (e.g. `$`, `€`, `%`), verified status indicator, subtitle context.

### 2. Bar Chart (`bar`)
- **Purpose:** Categorical comparison and ranking (e.g. Sales by Product Category, Region, Channel).
- **DuckDB Operation:** Group-by query `SELECT {group_by}, {AGG}({metric}) FROM {parquet} GROUP BY {group_by} ORDER BY agg_val DESC LIMIT {limit}`.
- **Features:** Responsive SVG rendering, hover tooltips with values and percentages, custom color palette.

### 3. Line Chart (`line`)
- **Purpose:** Continuous temporal trend analysis (e.g. Monthly Revenue, Daily Active Users).
- **DuckDB Operation:** Time-series date truncation query `date_trunc('{interval}', {time_column})`.
- **Granularities:** `day`, `week`, `month`, `quarter`, `year`.
- **Features:** Smooth SVG polyline, data points with interactive hover tooltips, endpoint time labels.

### 4. Area Chart (`area`)
- **Purpose:** Volume progression over time.
- **DuckDB Operation:** Time-series aggregation.
- **Features:** Signature Peacock Teal gradient fill, clean baseline curve.

### 5. Donut & Pie Chart (`donut`, `pie`)
- **Purpose:** Proportional composition of a whole.
- **DuckDB Operation:** Group-by query with Top-N categorization.
- **Features:** SVG radial wedges, center summary metric, color-coded legend with percentage shares.

### 6. Scatter Plot (`scatter`)
- **Purpose:** Bivariate correlation between two continuous numeric variables.
- **DuckDB Operation:** Dual-metric extraction `SELECT {x_col}, {y_col}, {label_col} FROM {parquet}` with null filtering.
- **Features:** 2D Cartesian grid, hover coordinates and labels.

### 7. Data Table (`table`)
- **Purpose:** Detailed tabular inspection and record validation.
- **DuckDB Operation:** Parameterized SQL query with sorting and row limits.
- **Features:** Sticky header, striped rows, horizontal scrolling for wide schemas.

### 8. Text & Insight Block (`text`)
- **Purpose:** Executive commentary, meeting notes, methodology explanations.
- **Features:** Clean markdown typography, customizable color accent.

---

## REST Widget Endpoints

| Endpoint | Method | Role | Description |
| :--- | :---: | :---: | :--- |
| `/api/v1/dashboards/{id}/widgets` | `POST` | Owner, Admin, Editor | Add widget to dashboard |
| `/api/v1/dashboards/{id}/widgets/{widget_id}` | `PUT` | Owner, Admin, Editor | Update widget configuration & dimensions |
| `/api/v1/dashboards/{id}/widgets/{widget_id}` | `DELETE` | Owner, Admin, Editor | Delete widget |
| `/api/v1/dashboards/{id}/widgets/{widget_id}/query` | `POST` | Viewer+ | Execute DuckDB calculation with optional filter overrides |

