# DataLens — AI Analytics Engine Architecture

## 1. Architectural Philosophy: The Calculation Divide

In DataLens, the foundational principle of AI business intelligence is **The Calculation Divide**:

```
+-------------------------------------------------------------+
|                     Natural Language Query                  |
|          "Which sales region had the highest revenue?"       |
+-------------------------------------------------------------+
                              │
                              ▼
+─────────────────────────────────────────────────────────────+
|               AI / LLM Interpretation Layer                 |
|   Role: Plan Synthesis ONLY (Zero Numerical Calculation)    |
|   Output: Validated JSON AnalyticalPlan                     |
+─────────────────────────────────────────────────────────────+
                              │
                              ▼
+─────────────────────────────────────────────────────────────+
|               Deterministic Validation Layer                |
|   PlanValidator checks column existence, types & operators  |
+─────────────────────────────────────────────────────────────+
                              │
                              ▼
+─────────────────────────────────────────────────────────────+
|              Deterministic Calculation Authority            |
|   DuckDB SQL Engine on local columnar Parquet storage       |
|   100% Deterministic, Auditable, Reproducible Output        |
+─────────────────────────────────────────────────────────────+
                              │
                              ▼
+─────────────────────────────────────────────────────────────+
|               Grounding & Presentation Layer                |
|   - AI Narrative strictly bounded by DuckDB facts           |
|   - Persistent AnalysisRun in PostgreSQL                    |
|   - Structured KPI Cards, Chart Views & Data Tables         |
+─────────────────────────────────────────────────────────────+
```

### Strict Architectural Boundaries
1. **The LLM is Never the Calculator:** The LLM does not perform math, aggregate numbers, or estimate trends.
2. **No Arbitrary Code Execution:** The LLM does not generate executable Python scripts or raw SQL queries executed directly by the server. It produces an AST-like JSON plan conforming to `AnalyticalPlan`.
3. **DuckDB is the Sole Authority:** All calculations (sums, averages, medians, trends, IQR, outliers) are computed by `AnalyticsEngine` in DuckDB.
4. **Data Minimization:** Only minimal schema summaries (column names, types, top 3 sample values) are sent to the LLM. Raw dataset records are never exposed to external APIs.

---

## 2. Request Lifecycle & Orchestration

The `AIAnalyticsOrchestrator` manages the end-to-end pipeline:

1. **Schema Context Preparation:**
   Extracts `columns` and `inferred_type` from the Parquet manifest (`version.storage_key`). Sample values are capped at 3 items per column.
2. **Intent Parsing:**
   The AI provider maps the user query into an `AnalyticalPlan` JSON.
   If AI is disabled or fails, the orchestrator invokes `_heuristic_plan_fallback`.
3. **Strict Validation:**
   `PlanValidator.validate_and_normalize_plan` matches metric and group-by columns against physical schema metadata. Rejects invalid operations with `INVALID_PLAN_COLUMN` or `INCOMPATIBLE_AGGREGATION`.
4. **Engine Execution:**
   The plan is routed to the corresponding DuckDB analytical service:
   - `group_by` / `ranking` -> `AnalyticsEngine.compute_aggregation()`
   - `time_series` -> `AnalyticsEngine.compute_time_series()`
   - `data_quality` -> `AnalyticsEngine.compute_data_quality()`
   - `descriptive_statistics` -> `AnalyticsEngine.compute_descriptive_stats()`
5. **Persistence:**
   An `AnalysisRun` record is committed to PostgreSQL with `status="completed"`, `execution_time_ms`, and the deterministic `result_summary`.
6. **Executive Grounding:**
   The AI provider generates an executive narrative referencing ONLY the DuckDB results. If the AI service fails or is disabled, a deterministic fallback narrative is returned.

---

## 3. Endpoints Overview

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/ai/status` | `GET` | Viewer+ | Reports AI provider readiness and model status. |
| `/api/v1/ai/ask` | `POST` | Viewer+ | End-to-end natural-language query processing. |
| `/api/v1/ai/clarify` | `POST` | Viewer+ | Clarifies ambiguous questions with conversation history. |
| `/api/v1/ai/explain` | `POST` | Viewer+ | Generates a fresh executive explanation for an existing `AnalysisRun`. |

