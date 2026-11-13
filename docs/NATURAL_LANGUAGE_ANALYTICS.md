# Natural Language Analytics Engine

## Overview
The Natural Language Analytics (NLA) Engine enables business users to query and analyze datasets using plain English, German, or informal business vocabulary without needing technical SQL or Python skills.

## Supported Analytical Capabilities

| Intent Category | Supported Questions | Planning Resolution |
| :--- | :--- | :--- |
| **Scalar Aggregations** | "What was total revenue?", "How many units were sold?" | Aggregation (`SUM`, `COUNT`, `AVG`) without grouping; returns KPI summary cards. |
| **Ranking & Extremes** | "Top 5 sales representatives", "Lowest performing region" | Orders by metric descending/ascending with configured `limit`. |
| **Time Trends & Periods** | "Monthly revenue growth this year", "Daily sales in January" | Buckets by time period (`DATE_TRUNC`) with chronological ordering for line visualization. |
| **Proportion & Contribution**| "What percentage of sales does Enterprise represent?" | Window function `ROUND(metric_value / NULLIF(SUM(metric_value) OVER (), 0) * 100, 2)` for donut/pie charts. |
| **Comparative Analytics** | "Compare Q1 revenue to Q2", "Sales versus previous month" | Calculates absolute and percentage period-over-period differences. |
| **Diagnostic Inquiries** | "Why did North region sales decrease?" | Multi-dimensional breakdowns isolating variances and outlier contributors. |

## Query Lifecycle
1. **Input Normalization**: Removes extraneous filler words and parses intent tokens.
2. **Ambiguity Evaluation**: Checks question breadth against ambiguity heuristics.
3. **Semantic Resolution**: Queries the Phase 6B semantic layer for measures, dimensions, and metrics.
4. **Context Merging**: If part of an active session, pulls forward active metrics, date ranges, and categorical filters.
5. **Execution & Evidence**: Executes query in DuckDB, generates fact cards, verifies facts against explanation, and produces charts.

