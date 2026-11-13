# Phase 4C: Advanced Interactive Visualization Engine Architecture

## 1. System Overview

DataLens Phase 4C upgrades the Interactive Dashboard Builder (introduced in Phase 4A) into an enterprise-class Business Intelligence visualization platform. It natively combines:
- 20+ specialized chart types across 4 distinct analytical categories.
- Contextual interactive drill-down hierarchies (temporal and categorical).
- Cross-filtering across dashboard widgets with bi-directional synchronization.
- Comparative analytics (Period-over-Period, Year-over-Year, Target vs Actual).
- Visual business annotations, threshold markers, and reference lines.
- Deterministic, zero-fabrication calculations powered by DuckDB against partitioned Parquet datasets.

---

## 2. Component Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DataLens Dashboard Studio                       │
│                                                                        │
│  ┌─────────────────────── Dashboard Header ────────────────────────┐   │
│  │ Controls: Edit Mode, Save, Export (PDF/XLSX/CSV), Cross-Filter Bar│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌────────────────────── Cross-Filtering Engine ────────────────────┐  │
│  │ Coordinates clicked dimensions across widgets: Region, Category  │  │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌────────────────────── 12-Column Responsive Grid ─────────────────┐  │
│  │                                                                 │  │
│  │  ┌───────────────────────┐  ┌────────────────────────────────┐  │  │
│  │  │  Widget: Stacked Bar  │  │  Widget: Treemap / Funnel      │  │  │
│  │  │  Drill-Down: Q1->Jan  │  │  Cross-Filter Trigger          │  │  │
│  │  │  Annotations: Target  │  │  Comparative Analytics: YoY    │  │  │
│  │  └───────────────────────┘  └────────────────────────────────┘  │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP /api/v1/dashboards/:id/widgets/:id/query
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI & DuckDB Backend                        │
│                                                                        │
│  ┌───────────────┐   ┌──────────────────┐   ┌───────────────────────┐  │
│  │ Dashboard     │   │ AnalyticsEngine  │   │ DuckDB Execution      │  │
│  │ Service       │──▶│ Query Builder    │──▶│ Aggregations, Window  │  │
│  │ Validation    │   │ Filter Injection │   │ Functions, Quantiles  │  │
│  └───────────────┘   └──────────────────┘   └───────────────────────┘  │
│                                                         │              │
│                                                         ▼              │
│                                                Partitioned Parquet     │
│                                                Datasets & Manifests    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow & Interactivity

1. **Drill-Down**:
   - The user configures a dimension hierarchy: `['year', 'quarter', 'month']` or `['category', 'subcategory', 'product']`.
   - On clicking a data point, the widget sets an internal drill-level filter and shifts grouping to the child dimension.
   - Breadcrumbs allow instant navigation up the hierarchy.

2. **Cross-Filtering**:
   - The user clicks a slice, bar, or funnel stage in Widget A.
   - The dashboard updates a shared `activeCrossFilters` state (`{ column: 'region', value: 'North' }`).
   - All other widgets receive the cross-filter as an override filter condition and re-query DuckDB, while Widget A remains highlighted.

3. **Comparative Analytics**:
   - Widget query configuration specifies comparison modes (`prior_period`, `yoy`, `target`).
   - DuckDB calculates base value, comparison value, absolute difference, and percentage change without zero-division errors.

