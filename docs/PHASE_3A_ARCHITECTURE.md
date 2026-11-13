# DataLens — Phase 3A: AI Analytics Foundation & Natural Language Business Intelligence
## Architectural Blueprint & Technical Audit

---

## 1. Executive Summary & Core Architectural Principle

Phase 3A introduces a production-grade, enterprise-safe AI analytics layer to DataLens, empowering business users to ask natural-language business questions about their uploaded datasets.

### The Non-Negotiable Rule of Separation of Concerns:
```
┌────────────────────────────────────────────────────────┐
│                   NATURAL LANGUAGE                     │
│         User Question: "Which product generated        │
│             highest revenue in Q3 2025?"               │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                AI INTERPRETATION LAYER                 │
│         • OpenAI / Provider Abstraction                │
│         • Intent Recognition & Schema Grounding        │
│         • Generates Structured Analytical Plan (JSON)   │
│         • ZERO numerical calculation / NO arbitrary SQL│
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           DETERMINISTIC VALIDATOR & ENGINE             │
│         • Schema & Data Type Compatibility Validator   │
│         • DuckDB Parquet In-Memory Execution Engine    │
│         • Mathematical Calculation Authority (100%)    │
│         • Persists immutable AnalysisRun evidence      │
└──────────────────────────┬─────────────────────────────┘
                           │ Actual Verified Results
                           ▼
┌────────────────────────────────────────────────────────┐
│                AI EXPLANATION LAYER                    │
│         • Explains verified facts from DuckDB          │
│         • Identifies peak categories & meaningful trends│
│         • Never modifies numbers or fabricates trends  │
└────────────────────────────────────────────────────────┘
```

1. **The LLM is strictly an interpreter and narrator:** It translates natural language into structured analytical plan schemas and explains verified numerical results in plain English.
2. **DuckDB and deterministic services remain the sole calculation authority:** The LLM is **never** permitted to calculate, fabricate, alter, or synthesize numbers.
3. **No Arbitrary Code/SQL Execution:** The LLM outputs structured Pydantic JSON plans (`intent`, `metric`, `dimensions`, `filters`, `sort`, `limit`). It **never** executes raw SQL or arbitrary Python scripts.
4. **Data Privacy & Minimal Ingestion:** Raw dataset rows are **never** transmitted to the LLM. Only dataset column metadata (names, inferred types, sample categories) and final summarized calculation metrics are provided to prompt contexts.

---

## 2. Codebase Audit of Existing Foundations

### 2.1 Backend Persistence & Data Access
- **Database Engine:** PostgreSQL 18.6 with async SQLAlchemy 2.0 and Alembic migrations at `20261111_0003 (head)`.
- **Tenant Isolation:** All datasets, versions, analysis runs, and reports are strictly scoped to `workspace_id`. Access is governed by FastAPI dependencies:
  `require_workspace_role(["owner", "admin", "editor", "viewer"])`.
- **Dataset Storage:** Raw files stored in `storage_data/uploads/`; processed datasets partitioned into Apache Parquet chunks in `storage_data/processed/` with a manifest linking column schemas, data types, and row counts.
- **Analytical Execution:** `AnalyticsEngine` (`backend/app/services/analytics/engine.py`) provides in-memory DuckDB zero-copy queries on Parquet files for profiling, descriptive statistics, group-by aggregations, time-series, data quality audits, and version comparisons.
- **Run Tracking:** The `AnalysisRun` model records `dataset_id`, `dataset_version_id`, `analysis_type`, `parameters` (JSONB), `result_summary` (JSONB), `status`, and `execution_time_ms`.

### 2.2 Frontend Architecture
- **Ask Your Data:** Located at `src/pages/ask/` with component hierarchy:
  - `AskYourData.tsx`: Manages active conversation sessions, selected datasets, question inputs.
  - `components/ActiveChatState.tsx`: Renders conversational thread, direct answer text, KPI cards, interactive charts (Bar, Line, Pie), structured data tables, business insights, follow-up chips, and expandable **"How this was calculated"** evidence blocks.
  - `components/WelcomeState.tsx`: Empty state with suggestion chips.
  - `components/DatasetIntelligencePanel.tsx`: Schema inspection and quick action questions.
  - `components/ConversationSidebar.tsx`: Multi-session history.
- **API Client:** `src/services/apiClient.ts` provides typed wrappers (`AuthApi`, `DatasetApi`, `AnalyticsApi`, `ReportApi`).
- **Phase 1B Client Fallback:** `src/services/askAnalyticsService.ts` executes browser-side deterministic analytics for offline or local IndexedDB datasets.

---

## 3. Proposed Phase 3A Architecture

### 3.1 AI Provider Abstraction (`app/services/ai/`)
To decouple business analytics from third-party vendor SDKs, an interface-driven architecture will be implemented:

```
app/services/ai/
├── __init__.py
├── base.py              # Abstract Base Class: AIProvider
├── openai_provider.py   # OpenAI Python SDK implementation (gpt-4o / gpt-4o-mini)
├── factory.py           # Provider Factory with graceful offline/disabled fallback
├── schemas.py           # Analytical plan schemas, clarification, explanation models
├── planner.py           # Converts natural language query -> Structured Plan
├── validator.py         # Validates plan against real dataset Parquet schema
└── explainer.py         # Grounds explanation in DuckDB calculation results
```

### 3.2 Configuration Parameters (`backend/app/core/config.py`)
Loaded via Pydantic `BaseSettings`:
- `AI_PROVIDER`: `str = "openai"` (default)
- `AI_API_KEY`: `str | None = None`
- `AI_MODEL`: `str = "gpt-4o-mini"`
- `AI_TIMEOUT_SECONDS`: `int = 30`
- `AI_MAX_RETRIES`: `int = 2`
- `AI_ENABLED`: `bool = False`

### 3.3 Supported Analytical Intents
1. `dataset_summary`: Overview of row counts, key dimensions, and column profiles.
2. `descriptive_statistics`: Mean, median, min, max, variance, standard deviation, IQR for numeric metrics.
3. `group_by`: Multi-category aggregation (SUM, AVG, MIN, MAX, COUNT) with percentage share-of-total.
4. `filtered_aggregation`: Metric calculations subject to parameterized predicates (`eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `contains`, `between`).
5. `time_series`: Temporal grouping (monthly, quarterly, yearly) with period-over-period growth calculation.
6. `ranking`: Top-N / Bottom-N categorical ordering by calculated metric.
7. `comparison`: Period-over-period or dimension-to-dimension variance analysis.
8. `data_quality`: Auditing missing values, duplicate records, commercial negatives, and statistical outliers.

### 3.4 API Endpoints to Expose (`/api/v1/ai`)
- `POST /api/v1/ai/ask`: Accepts `{ dataset_id, version_id?, question, conversation_context? }`. Generates plan, validates schema, queries DuckDB, persists `AnalysisRun`, asks LLM to explain verified results, and returns structured message with evidence.
- `POST /api/v1/ai/clarify`: Resolves ambiguous questions when mandatory dimensions/metrics are unspecified.
- `POST /api/v1/ai/explain`: Re-explains an existing verified `analysis_run_id` with new tone or audience parameters.
- `GET /api/v1/ai/status`: Reports provider availability, configured model, and whether AI features are enabled (never exposing API keys).

---

## 4. Security, Isolation & Safety Controls

1. **Zero Prompt Injection through Data:** Dataset cell values are never passed into system instruction blocks. The LLM receives schema definitions in strict JSON and returns structured plan objects via JSON Schema mode (`response_format={"type": "json_object"}`).
2. **Workspace Isolation:** Every request verifies that `dataset_id` belongs to the requesting user's active `workspace_id`.
3. **Execution Parameterization:** DuckDB queries use parameter markers (`?`) and sanitized identifier escaping (`"column_name"`).
4. **Deterministic Fallback:** If `AI_ENABLED=false` or the provider times out, the system automatically detects keywords to execute deterministic calculations and returns evidence with a note: *"AI explanation unavailable; verified deterministic calculations provided."*

---

## 5. Verification & Rollout Plan

- **Stage 1:** Provider Abstraction & Settings.
- **Stage 2:** Analytical Plan Pydantic Schemas & Prompt Engineering.
- **Stage 3:** Plan Validator & DuckDB Engine Integration.
- **Stage 4:** Evidence Generation & AnalysisRun Persistence.
- **Stage 5:** Explanation Engine Grounding.
- **Stage 6:** Conversational Context & Follow-up Resolution.
- **Stage 7:** FastAPI Endpoints & RBAC.
- **Stage 8:** Frontend Ask Your Data Integration.
- **Stage 9:** Security & Reliability Hardening.
- **Stage 10:** Automated Unit, Mock, and Live Integration Testing.
- **Stage 11:** Documentation Delivery.

