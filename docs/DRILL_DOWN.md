# DataLens — Hierarchical Drill-Down Engine

This document details the hierarchical drill-down capabilities introduced in DataLens Phase 4C.

---

## 1. Overview & Conceptual Architecture

Hierarchical Drill-Down allows dashboard users to explore multidimensional datasets from a high-level summary down to granular operational details with a single click.

### Example Hierarchy Chains
- **Geographic**: `Region` $\rightarrow$ `Country` $\rightarrow$ `City`
- **Product Hierarchy**: `Department` $\rightarrow$ `Category` $\rightarrow$ `Subcategory`
- **Time Hierarchy**: `Year` $\rightarrow$ `Quarter` $\rightarrow$ `Month` $\rightarrow$ `Day`
- **Organizational**: `Business Unit` $\rightarrow$ `Division` $\rightarrow$ `Team`

---

## 2. Configuration & Schema Mapping

In the Widget Configuration Modal (`WidgetConfigModal.tsx`), users define hierarchy levels as a sequential list of column names:

```json
{
  "hierarchy_levels": ["region", "country", "city"]
}
```

The widget's backend query execution engine in `dashboard_service.py` evaluates the active drill state:
1. `drill_level`: Integer depth starting at $0$.
2. `drill_filters`: Accumulated filter conditions from previous drill steps:
   ```json
   [
     { "column": "region", "operator": "eq", "value": "North America" }
   ]
   ```
3. Effective grouping column resolved dynamically:
   ```python
   effective_group_col = hierarchy_levels[min(drill_level, len(hierarchy_levels) - 1)]
   ```

---

## 3. Frontend Interactivity & Breadcrumbs

`DashboardWidgetCard.tsx` manages the local drill-down lifecycle:
- **Click to Drill**: Clicking a bar, category label, or treemap slice appends a drill filter, increments `drillDepth`, and triggers a scoped query refresh.
- **Interactive Breadcrumb Navigation**: Renders an inline path at the top of the card:
  $$\text{All} > \text{North America} > \text{United States} \quad [\leftarrow \text{Back}]$$
  - Clicking any ancestor breadcrumb resets depth to that level.
  - Clicking `[Back]` steps up exactly one level.
- **Leaf Level Detection**: When the deepest hierarchy level is reached, further clicks trigger dashboard cross-filtering rather than additional drill attempts.

