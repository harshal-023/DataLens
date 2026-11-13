# DataLens — Interactive Dashboard Filtering System

## Overview

The **Dashboard Filtering System** allows users to slice, dice, and query metrics across an entire dashboard simultaneously.

When an active filter value changes, DataLens broadcasts the updated filter state to all compatible widgets connected to datasets containing the target column, re-executing calculations without a full page reload.

---

## Supported Filter Types

| Filter Type | Identifier | Supported Operators | UI Control | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Date Range** | `date_range` | `gte`, `lte`, `between` | Calendar dropdown / preset selections | Time horizons (e.g. 2025 onwards) |
| **Dropdown** | `dropdown` | `eq`, `neq` | Single-select select picker | Categorical dimensions (e.g. Region, Department) |
| **Multi-Select** | `multi_select` | `in` | Checkbox multi-select dropdown | Multi-category selections |
| **Numeric Range** | `numeric_range` | `gte`, `lte`, `between` | Number input box | Minimum thresholds (e.g. Orders >= $500) |
| **Text Search** | `text` | `contains`, `starts_with` | Search input with clear button | Text searching within customer names, SKU |

---

## Filter Synchronization Mechanics

1. **Client-Side Filter State:**
   - Maintained in React component state as a map of `column_name -> { column, operator, value }`.
   - Modifying any control invokes `onFilterChange` instantly.
2. **Selective Execution:**
   - When a widget is queried (`POST /api/v1/dashboards/{id}/widgets/{widget_id}/query`), active filters are forwarded in the request payload.
   - DuckDB parameterized queries append the filter clauses using `_build_where_clause()`.
3. **Reset Capability:**
   - Clicking `Reset all` immediately wipes all filter constraints and reverts all dashboard widgets to their baseline values.

---

## Filter REST APIs

| Endpoint | Method | Role | Description |
| :--- | :---: | :---: | :--- |
| `/api/v1/dashboards/{id}/filters` | `POST` | Owner, Admin, Editor | Add interactive filter to dashboard |
| `/api/v1/dashboards/{id}/filters/{filter_id}` | `PUT` | Owner, Admin, Editor | Update filter label, column, or defaults |
| `/api/v1/dashboards/{id}/filters/{filter_id}` | `DELETE` | Owner, Admin, Editor | Remove filter from dashboard |

