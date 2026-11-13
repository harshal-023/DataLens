# DataLens Data Transformation & Preparation Guide

## Overview

DataLens Phase 4B introduces a complete, enterprise-grade Data Transformation & Preparation Engine. Users can clean, combine, join, enrich, and transform multiple uploaded datasets into high-fidelity analytical models directly within their workspace before using them in dashboards, Ask Your Data, machine learning models, and automated reports.

## Key Capabilities

1. **Multi-Dataset Joining**: INNER, LEFT, RIGHT, and FULL OUTER joins with multi-column key pairs, collision renaming, and missing key detection.
2. **Dataset Merging & Appending**: UNION ALL and UNION DISTINCT modes with automatic column alignment and NULL padding for disparate schemas.
3. **Data Cleaning**:
   - NULL value handling: Drop rows, fill with constant, fill with column mean, median, or mode.
   - Deduplication: Deduplicate on whole rows or subset of unique key columns using window functions.
4. **Data Type Casting**: Cast between integer, float, string, boolean, date, and timestamp with safe `TRY_CAST`.
5. **String Operations**: Trim, uppercase, lowercase, capitalize, substring, and string replacement.
6. **Safe Calculated Columns & Formulas**: AST-based formula engine supporting arithmetic, comparisons, IF conditionals, COALESCE, and safe division (guaranteed zero division-by-zero crashes).
7. **Interactive Studio Workflow**:
   - Left panel: Multi-dataset catalog & schema browser.
   - Center canvas: Transformation step stack with re-ordering and configuration modals.
   - Right panel: Live interactive DuckDB preview table with row sampling and schema inspector.
8. **First-Class Derived Datasets**: Pipeline execution materializes immutable Parquet parts and JSON manifests with provenance records, making derived datasets immediately available across all DataLens modules.

---

## Architectural Flow

```
[Raw Datasets (Parquet)] 
         │
         ▼
[DuckDB In-Memory Execution] ── (Formula Engine AST)
         │
         ▼
[Sequential Transformation Steps: Join -> Clean -> Cast -> Formula -> Filter]
         │
         ├── Preview (Top 25 rows, schema inspect)
         │
         ▼
[Materialization: Part Parquet + Manifest JSON]
         │
         ▼
[PostgreSQL: Dataset + DatasetVersion + TransformationRun]
```

