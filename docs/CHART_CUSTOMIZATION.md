# DataLens — Chart Customization & Annotations Guide

This document describes the chart customization capabilities available in DataLens Phase 4C.

---

## 1. Widget Configuration Modal

The widget modal organizes visualization settings into intuitive sections:
1. **Categorized Type Selector**:
   - Filterable tabs: `All`, `Summary`, `Bar`, `Time Series`, `Statistical`, `Business`, `Standard`.
   - Clear cards showing widget titles, category labels, and brief descriptions.
2. **Dataset & Query Binding**:
   - Source dataset selection.
   - Metric column and math aggregation (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`).
   - Dimension bindings: primary category column, secondary series/stack column, and time interval.
   - Sort direction (`DESC`, `ASC`) and Top-N limit controls.
3. **Interactive Features**:
   - Hierarchical drill-down path definition.
   - Target benchmark value and comparative analytics mode.
4. **Formatting & Annotations**:
   - Currency and display unit formatting (`$`, `€`, `%`, `units`, `hrs`).
   - Threshold / reference line configuration (e.g. `80% Target SLA`).
5. **Grid Layout**:
   - Width selection (3, 4, 6, 8, 12 columns).
   - Height selection (3, 4, 6, 8 row units).

---

## 2. Annotations & Reference Lines

Widgets support threshold annotations rendered directly on the visualization canvas:
```json
{
  "annotations": [
    {
      "value": 85.0,
      "label": "Quarterly Target",
      "color": "#E05D52"
    }
  ]
}
```
- **Line & Bar Charts**: Renders a subtle horizontal dashed reference line across the plot area with a label badge positioned on the y-axis.
- **KPI Cards**: Displays a benchmark target indicator below the primary value.

