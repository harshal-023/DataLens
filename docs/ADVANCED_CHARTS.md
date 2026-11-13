# DataLens — Advanced Interactive Visualizations & Chart Catalog

This document details the complete suite of advanced business intelligence visualizations implemented in DataLens Phase 4C, categorized into four analytical families.

---

## 1. Summary Family

### KPI Metric Card (`kpi`)
- **Purpose**: Displays a headline scalar value with optional percentage change, period comparisons, and status indicators.
- **Data Source**: Aggregation (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`) of a single numerical column.
- **Comparative Support**: Integrates target comparison, period-over-period (MoM), and Year-over-Year (YoY) delta badges with directional coloring ($\uparrow$ teal for growth, $\downarrow$ red for drop).

### Gauge & Target Meter (`gauge`)
- **Purpose**: Radial SVG meter visualizing progress toward an explicit benchmark or quarterly quota.
- **Key Fields**:
  - `metric_column`: The actual recorded value.
  - `target_value`: The goal or benchmark value.
- **Interactions**: Dynamic color shift based on completion percentage ($<70\%$ slate, $70-99\%$ navy/amber, $\ge 100\%$ vibrant peacock teal).

---

## 2. Bar Family

### Standard Bar Chart (`bar`)
- **Purpose**: Categorical comparisons and rankings.
- **Key Fields**: `group_by_column`, `metric_column`, `aggregation`, `limit`, `sort_direction`.
- **Interactions**: Hover tooltips, click-to-drill, click-to-cross-filter.

### Stacked Bar Chart (`stacked_bar`)
- **Purpose**: Displays part-to-whole segment composition across categorical bars.
- **Data Shape**:
  ```json
  {
    "categories": ["North", "South", "East", "West"],
    "series": [
      { "name": "Hardware", "values": [12000, 8500, 14000, 9200] },
      { "name": "Software", "values": [8000, 6200, 9500, 7100] }
    ]
  }
  ```
- **Backend Execution**: DuckDB query pivoting `sub_group_by_column` with aggregated totals.

### Grouped Bar Chart (`grouped_bar`)
- **Purpose**: Side-by-side clustering of sub-series per categorical bucket.
- **Interactions**: Individual bar hover highlighting, segment cross-filtering.

### Horizontal Bar Chart (`horizontal_bar`)
- **Purpose**: Ideal for ranking categories with long textual labels (e.g., product names, customer accounts).
- **Interactions**: Direct category cross-filtering, proportional scaling.

### 100% Stacked Bar Chart (`percent_bar`)
- **Purpose**: Normalized proportional breakdown where every bar reaches 100%, emphasizing relative contribution over absolute magnitude.
- **Formula**:
  $$\text{Normalized Share}_i = \frac{V_i}{\sum_{k=1}^M V_k} \times 100\%$$

### Top-N Ranking (`top_n`)
- **Purpose**: Highlights top performers (e.g., Top 5 Sales Representatives) with ranked badges and contrast shading.

---

## 3. Time Series Family

### Standard Line & Area (`line`, `area`)
- **Purpose**: Continuous time trend monitoring.
- **Time Buckets**: `day`, `week`, `month`, `quarter`, `year`.
- **Backend Execution**: DuckDB `DATE_TRUNC(granularity, time_col)` aggregation.

### Multi-Line Series (`multi_line`)
- **Purpose**: Multiple trend lines plotted on a shared time axis, comparing dimensions over time (e.g. Sales across 4 regions).

### Stacked Area (`stacked_area`)
- **Purpose**: Cumulative volume over time, displaying both the macro trend and constituent components.

### Combo Chart (`combo`)
- **Purpose**: Dual-representation visualization combining Bar bars (for transactional volume) and Line trend (for conversion rate, revenue growth, or margin).

---

## 4. Statistical Family

### 2D Heatmap (`heatmap`)
- **Purpose**: Matrix intensity visualization crossing two categorical dimensions (e.g. Day of Week vs Hour, Region vs Product Line).
- **Color Scale**: 5-tier teal gradient intensity calculated via min-max normalization.

### Histogram (`histogram`)
- **Purpose**: Numerical frequency distribution across equidistant buckets.
- **DuckDB Execution**:
  - Computes $\min(X)$, $\max(X)$, and $\text{step} = (\max - \min) / \text{bins}$.
  - Dynamically calculates bin boundaries $[X_{\min} + i \cdot \text{step}, X_{\min} + (i+1) \cdot \text{step})$.

### Box & Whisker Plot (`box_plot`)
- **Purpose**: Five-number summary visualization showing median, quartiles ($Q_1, Q_3$), and whiskers ($1.5 \times \text{IQR}$).
- **DuckDB Functions**:
  - `QUANTILE_CONT(col, 0.25)` $\rightarrow Q_1$
  - `MEDIAN(col)` $\rightarrow Q_2$
  - `QUANTILE_CONT(col, 0.75)` $\rightarrow Q_3$
  - `MIN(col)` and `MAX(col)`

### Correlation Matrix (`correlation`)
- **Purpose**: Pearson correlation coefficients between all numerical features.
- **DuckDB Function**:
  `CORR(col_a, col_b)` returning normalized values between $-1.0$ and $+1.0$.

---

## 5. Business Family

### Hierarchical Treemap (`treemap`)
- **Purpose**: Nested rectangular area decomposition sized proportionally by metric magnitude.
- **Interactions**: Click to zoom into category segment or cross-filter.

### Waterfall Chart (`waterfall`)
- **Purpose**: Explains cumulative variance from a starting value to an ending value through sequential positive and negative contributions.
- **Color Coding**: Teal for additions ($+\Delta$), Red for deductions ($-\Delta$), Navy for starting and final balances.

### Pipeline Funnel (`funnel`)
- **Purpose**: Sequential stage tracking (e.g. Lead $\rightarrow$ Qualified $\rightarrow$ Proposal $\rightarrow$ Closed Won) with conversion percentage and drop-off rates between adjacent stages.

### Pareto Chart (`pareto`)
- **Purpose**: 80/20 rule identification. Displays sorted descending frequency bars alongside a cumulative percentage line.
- **Threshold**: Explicit dashed 80% reference line marking the "vital few" contributors.

