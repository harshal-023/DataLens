# DataLens – Non-Technical Widget Creation UX Specification

**Document:** `WIDGET_CREATION_UX.md`  
**Target Audience:** Non-technical business users, product managers, sales leaders, and analysts  
**Implementation:** `src/components/dashboards/WidgetConfigModal.tsx`

---

## 1. UX Transformation Overview

The previous widget configuration interface was a monolithic 920-line technical form that exposed raw database column names, SQL aggregation primitives (`COUNT_DISTINCT`, `AVG`, `SUM`), group-by clauses, grid width/height integers, and manual threshold inputs.

The redesigned experience transforms widget authoring into an intuitive **3-Step Guided Wizard** modeled after Power BI and Tableau:

```
[ Step 1: Choose Type ]  ──>  [ Step 2: Select Data ]  ──>  [ Step 3: Customize Appearance ]
```

---

## 2. Step 1: Choose What to Display

Users are presented with large visual cards with clean iconography, pastel wash backgrounds, and plain-language descriptions:

1. **KPI Card**: "Single headline summary with trend indicator"
2. **Bar Chart**: "Compare metrics across categories side-by-side"
3. **Line Chart**: "Track continuous trends and changes over time"
4. **Area Chart**: "Display volume magnitude and cumulative growth"
5. **Pie / Donut**: "Proportions and percentage breakdown of a whole"
6. **Data Table**: "Structured tabular rows and records view"
7. **Text / Insight**: "Executive summaries, conclusions, and notes"

### Advanced Visualizations Accordion
For advanced power users, a collapsible toggle reveals specialized statistical and business visuals:
- Radial Gauge (Progress against target)
- Horizontal Bar (Long-label rankings)
- Stacked & Grouped Bar (Multi-series composition)
- Heatmap (2D matrix intensity)
- Histogram (Numerical frequency distribution)
- Funnel Chart (Conversion drop-offs)
- Waterfall (Positive/negative increment decomposition)
- Treemap (Nested area hierarchy)

---

## 3. Step 2: Select Your Data (Plain Language Questions)

Step 2 eliminates database jargon by asking direct business questions with intelligent auto-detection:

| Technical Concept | New Business-Friendly Question | Intelligent Behavior |
| :--- | :--- | :--- |
| **Dataset Selection** | *"Which dataset should we use?"* | Dropdown displaying dataset name with human-readable record count (e.g. `Business Sales (4,115 rows)`). |
| **Metric Column** | *"What do you want to measure?"* | Auto-filtered to numerical columns (e.g. `Revenue`, `Sales`, `Order Amount`). Replaces underscores with spaces. |
| **Aggregation Function** | *"How should we calculate it?"* | Friendly options: `Sum (Total)`, `Average (Mean)`, `Count of records`, `Unique count`, `Minimum`, `Maximum`. Defaults to `Sum (Total)`. |
| **Dimension / Group By** | *"What should we compare it by?"* | Auto-filtered to categorical columns (e.g. `Region`, `Product Category`, `Customer Segment`). |
| **Time Dimension** | *"What date or time field shows the trend?"* | Auto-filtered to date/timestamp fields (e.g. `Order Date`, `Transaction Month`). |

### Real-Time Live Visual Preview
The right 5 columns of Step 2 feature a **Live Visual Preview card**. As users change calculations or fields, the preview updates immediately with representative sample data, giving users instant visual feedback before saving.

---

## 4. Step 3: Customize Appearance & Styling

Step 3 provides aesthetic and formatting controls:

1. **Widget Title**: Auto-generated from selected metric and category (e.g. *"Total Sales by Region"*), with instant inline editing.
2. **Optional Subtitle**: Explanatory context (e.g. *"Current Fiscal Year vs. Target"*).
3. **Color Palette Selector**: 7 pre-built color themes (Ocean, Sunset, Forest, Royal, Business, Vibrant, Monochrome) with live color swatch indicators.
4. **Custom Accent Color**: Color picker and hex input for exact brand alignment.
5. **Number Format / Currency**: Selector for `Indian Rupee (₹)`, `US Dollar ($)`, `Euro (€)`, `Percentage (%)`, or `Plain Number`.
6. **Display Toggles**: One-click checkboxes for *"Show Legend"* and *"Show Data Labels"*.
7. **Collapsible Advanced Options**: Collapsed accordion for Limit (max categories), Sort Direction (Highest first / Lowest first), and Grid Width (1/4, 1/3, 1/2, or Full width).

---

## 5. Friendly Validation & Error Handling

- Form validation checks for required fields without intimidating users.
- If a user omits a title, an inline toast suggests a contextual default title.
- If a dataset query returns 0 rows or is missing a dimension, the card renders a friendly illustration:
  `"Configure your widget: This widget needs a metric and category selected to display data."` with an action button `[ Configure Widget ]` that re-opens the wizard.

