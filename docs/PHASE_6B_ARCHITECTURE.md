# Phase 6B Architecture: Dataset-Aware AI Intelligence & Business Semantic Layer

## 1. Executive Summary
DataLens Phase 6B transforms the platform from a conventional BI tool into a dataset-aware intelligence system. The system understands uploaded datasets, column semantics, business domains, relationships between tables, and reusable business metrics. Users can query data using natural business language without repeatedly defining column meanings or manual calculations.

```
+-----------------------------------------------------------------------------------------------+
|                                      DATALENS STUDIO                                          |
|                                                                                               |
|  [ Data Studio ] <---> [ Intelligence Center ] <---> [ Ask Your Data ] <---> [ Dashboards ]  |
+-----------------------------------------------------------------------------------------------+
                                               |
                                               v
+-----------------------------------------------------------------------------------------------+
|                                    BUSINESS SEMANTIC LAYER                                    |
|                                                                                               |
|   +-----------------------+     +-------------------------+     +--------------------------+  |
|   | Column Semantics      |     | Business Context        |     | Metric Registry          |  |
|   | - Logical/Phys types  |     | - Business Domain       |     | - Formula AST validator  |  |
|   | - Business Names      |     | - Analytical Purpose    |     | - Zero-div protection    |  |
|   | - Multi-signal types  |     | - Domain KPIs           |     | - Metric versions        |  |
|   | - User confirmation   |     | - Business entities     |     | - DuckDB calculation     |  |
|   +-----------------------+     +-------------------------+     +--------------------------+  |
|                                               ^                                               |
+-----------------------------------------------|-----------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
|                                DATASET INTELLIGENCE PROFILER                                  |
|                                                                                               |
|  - Bounded DuckDB queries over immutable Parquet files (quantiles, IQR, duplicates)           |
|  - Candidate Primary Key (100% uniqueness, 0 nulls) and Foreign Key detection                |
|  - Relationship Discovery (referential coverage, cardinality 1:1, 1:N, N:M, join warnings)  |
|  - Quality Scoring (100 - penalties) and anomaly warnings                                    |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
|                              AI CONTEXT BUILDER & HYBRID ROUTER                               |
|                                                                                               |
|  - Sanitized schema prompts (business names, dimensions, measures, approved metrics)          |
|  - Zero raw row transmission to Cloud Gemini                                                  |
|  - Strict local-only routing for CONFIDENTIAL & RESTRICTED data                               |
+-----------------------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Pillars

### 2.1 Dataset Intelligence Profiler
- **Engine:** Bounded DuckDB in-memory analytical aggregation.
- **Scope:** Runs against immutable `DatasetVersion` Parquet parts on disk.
- **Signals:** Multi-signal inference incorporating column naming patterns, physical data types, null fractions, cardinality ratios, IQR numeric distributions, and sample content regex.
- **Output:** Stored in PostgreSQL `dataset_profiles` table, tied to the immutable dataset version.

### 2.2 Semantic Layer & Business Glossary
- **Column Semantic Mappings (`column_semantic_mappings`):**
  - Logical types (`integer`, `float`, `boolean`, `date`, `datetime`, `string`).
  - Semantic classifications (`currency`, `percentage`, `quantity`, `customer_identifier`, `product_identifier`, `transaction_identifier`, `email`, `phone`, `geographic_region`, `address`, `status`, `category`).
  - Mapping statuses (`AI_SUGGESTED`, `USER_CONFIRMED`, `SYSTEM_INFERRED`).
  - Strict preservation: Re-running profiling NEVER overrides `USER_CONFIRMED` mappings.
- **Schema Evolution & Version Inheritance:** When a new `DatasetVersion` is materialized (e.g. via replacement upload or automated refresh), verified mappings are automatically inherited.

### 2.3 Cross-Dataset Relationship Discovery
- **Workspace-Scoped Discovery:** Compares column pairs across tables in the same workspace.
- **Cardinality Inference:**
  - `ONE_TO_ONE`: Source is PK, Target is PK.
  - `MANY_TO_ONE`: Source is FK/non-unique, Target is PK.
  - `ONE_TO_MANY`: Source is PK, Target is non-unique.
  - `MANY_TO_MANY`: Neither column is unique; flags an explicit **Join Cardinality Warning** to protect users against row multiplication during joins.
- **Referential Overlap Check:** Uses bounded DuckDB queries to calculate exact distinct value overlap ratios.

### 2.4 Business Context Engine
- **Domain Classification:** Automatically identifies business domains (`SALES`, `FINANCE`, `MARKETING`, `CUSTOMER_ANALYTICS`, `OPERATIONS`, `INVENTORY`, `HUMAN_RESOURCES`, `LOGISTICS`, `GENERAL_BUSINESS`).
- **Context Synthesis:** Proposes standard domain KPIs, business entities, key dimensions, and analytical assumptions.

### 2.5 Metric Intelligence Engine
- **Safe Formula Parsing:** Uses Python `ast.parse` in `eval` mode with strict AST node whitelisting. Absolutely NO `eval()` or `exec()`.
- **Division-by-Zero Safety:** Automatically compiles expressions like `Revenue / Orders` to `Revenue / NULLIF(Orders, 0)`.
- **DuckDB Execution:** Directly computes aggregate metric values on Parquet storage without intermediate file conversions.
- **Metric Versioning:** Modifications increment version numbers and append immutable records to `metric_versions`.

### 2.6 AI Context Builder
- Prepares token-budgeted, relevance-ranked prompt contexts for downstream AI engines (Ask Your Data, Business Reports, ML Insights).
- Invariant: Zero raw row records are ever transmitted to Google Gemini.

