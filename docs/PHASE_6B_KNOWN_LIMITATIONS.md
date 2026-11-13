# Phase 6B Known Limitations & Operational Considerations

## 1. High-Cardinality String Text Columns
- When profiling text columns with very high distinct counts (e.g. unique descriptions or unstructured free-form comments), quantile calculations are skipped and distinct hashing is bounded to prevent excessive memory overhead in DuckDB.

---

## 2. Cross-Dataset Disconnected Workspaces
- By architectural design, relationship discovery operates strictly within the boundary of a single workspace. Datasets belonging to different workspaces cannot be joined or linked, ensuring multi-tenant data isolation.

---

## 3. Large Multi-Gigabyte Parquet Profiling
- For massive datasets exceeding hundreds of millions of rows, full quantile computations (`QUANTILE_CONT`) can take several seconds. Background profiling tasks or bounded sampling (e.g. `USING SAMPLE 10%`) can be configured in future scaling milestones to reduce execution duration on commodity hardware.

---

## 4. Complex Non-Linear Metric Expressions
- The safe metric formula engine currently supports arithmetic expressions (`+`, `-`, `*`, `/`), parenthesized sub-expressions, and standard aggregations (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`, `ROUND`, `ABS`, `COALESCE`). Advanced statistical functions like moving standard deviations or non-linear regressions should be executed via DataLens Transformation Pipelines or ML Analytics.

