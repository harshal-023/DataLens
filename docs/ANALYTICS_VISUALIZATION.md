# Analytics Visualization Recommendation Engine

## Overview
`NLAVisualizer` automatically recommends and configures the most appropriate visualization type for analytical answers based on data shapes and query intent.

## Heuristic Mapping Rules

| Data Shape / Intent | Recommended Chart | Reasoning |
| :--- | :--- | :--- |
| Single scalar metric | **KPI Card** | Clean presentation of headline numbers and benchmarks without chart clutter. |
| Time series (`intent="trend"` or date period column) | **Line Chart** | Optimal for displaying continuous temporal patterns, trends, and inflections. |
| Categorical grouping / Ranking (`limit <= 10`) | **Bar Chart** | Clear horizontal or vertical comparison of magnitude across discrete segments. |
| Contribution / Share of total (`<= 7` categories) | **Donut / Pie Chart** | Effectively visualizes percentage proportions of a whole with windowed share calculations. |
| High cardinality or multi-measure queries | **Data Table** | Structured tabular display with sortable headers, formatted values, and CSV export. |

## Interactive View Toggles
The user interface allows analysts to toggle effortlessly between:
- Bar Chart
- Line Chart
- Donut Chart
- Data Table
- CSV Export download

