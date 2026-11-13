# Phase 7A: End-to-End Workflow & User Journey Audit

## 1. Journey A: Registration → Login → Workspace
- **Trace**:
  1. User navigates to `/signup`, enters name, email, and password.
  2. Backend validates password complexity via `Argon2id` hasher, creates `User` record, generates default `Workspace`, and creates `WorkspaceMembership` with role `OWNER`.
  3. Returns JWT access token (15-min lifespan) and refresh token (7-day lifespan in `refresh_sessions`).
  4. Frontend stores token, initializes `AuthContext`, and redirects to `/dashboard`.
- **Audit Assessment**: **PASS**. Tested in `test_auth_unit.py` and frontend auth tests. No broken transitions.

---

## 2. Journey B: Upload File → Profiling → Parquet Storage
- **Trace**:
  1. User drags CSV or XLSX into `/data` (Data Studio).
  2. File is uploaded to `POST /api/v1/datasets/upload`. Backend parses chunks via PyArrow/OpenPyXL, validates schema, converts to Parquet, and writes to `datasets/{workspace_id}/{dataset_id}/v1/data.parquet`.
  3. `DatasetIntelligenceProfiler` automatically computes statistical summaries, null counts, semantic types, and quality scores.
  4. Frontend reflects dataset card with quality score badge and row count.
- **Audit Assessment**: **PASS**. Validated via `test_dataset_processor.py` and `test_dataset_intelligence.py`.

---

## 3. Journey C: Dataset → Cleaning & Transformation → Derived Dataset
- **Trace**:
  1. User navigates to `/data-preparation`, creates a new pipeline pointing to an existing dataset version.
  2. Adds transformation steps: filter rows, cast types, formula calculation, handle nulls.
  3. Formula input is checked via AST validator (`validate-formula`).
  4. User clicks "Run Pipeline" (`POST /pipelines/{id}/run`). Backend executes steps sequentially in DuckDB, materializing a new derived `Dataset` and `DatasetVersion`.
- **Audit Assessment**: **PASS**. Zero code injection risk; tested in `test_transformations.py`.

---

## 4. Journey D: Dataset → Dashboard → Filters → Drill-Down
- **Trace**:
  1. User opens `/dashboards`, creates a dashboard, and adds widgets (Bar, Line, Area, KPI).
  2. Configures metric aggregation (SUM, AVG) and group-by dimension.
  3. User selects a date range or category filter on the dashboard header.
  4. Active filter values propagate to all chart widgets simultaneously via cross-filtering listeners.
- **Audit Assessment**: **PASS**. Tested in `test_dashboards.py` and `dashboards.test.ts`.

---

## 5. Journey E: Ask Your Data → Conversational Analytics → Grounding
- **Trace**:
  1. User enters natural language prompt (e.g., "What was our quarterly revenue by region?").
  2. `NLAQueryPlanner` resolves entities and selects approved semantic metrics.
  3. `NLASafeQueryCompiler` compiles a deterministic DuckDB SQL statement and executes it on Parquet.
  4. `NLAEvidenceVerifier` inspects AI explanation text, ensuring every cited number matches computed results.
  5. If an ungrounded number is detected, the engine flags a hallucination warning and displays deterministic cards.
- **Audit Assessment**: **PASS**. Validated in `test_nl_analytics.py`.

---

## 6. Journey F: Dataset → Business Analyst → Insights → Lifecycle
- **Trace**:
  1. User triggers autonomous sweep on `/business-analyst` or schedule executes in background.
  2. `TrendEngine`, `AnomalyEngine`, `RiskEngine`, and `OpportunityEngine` scan metrics.
  3. Findings are prioritized into `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, and `INFORMATIONAL`.
  4. User clicks an insight, inspects fact vs inference in the Detail Drawer, assigns to a team member, posts comments, and updates status to `ACKNOWLEDGED` or `RESOLVED`.
  5. Status change is recorded in immutable `insight_assessments` audit table.
- **Audit Assessment**: **PASS**. Verified in `test_business_analyst.py` and `business_analyst.test.ts`.

---

## 7. Journey G: Dashboard/Analysis → Report Generation → Export
- **Trace**:
  1. User triggers report generation from `/reports/new` using an executive template.
  2. Backend renders sections into PDF (ReportLab), DOCX (python-docx), XLSX (OpenPyXL), or CSV.
  3. User clicks download link (`GET /api/v1/reports/{id}/download`).
  4. Multi-format binaries download cleanly with proper MIME types.
- **Audit Assessment**: **PASS**. Tested in `test_reports.py`.

---

## 8. Journey H: External Connector → Import → Refresh → New Version
- **Trace**:
  1. User navigates to `/data-sources`, configures PostgreSQL/MySQL/S3 connector.
  2. Clicks "Discover Schema" to inspect tables and columns.
  3. Selects table and clicks "Import Now". Backend materializes Parquet dataset.
  4. Scheduled refresh rule detects changes and creates updated `DatasetVersion`.
- **Audit Assessment**: **PASS** (Mocked connectors verified in `test_connectors.py`; live third-party cloud instances marked UNVERIFIED due to external credential requirement).

---

## 9. Journey I: Scheduled Job → Execution → Retry → Notification
- **Trace**:
  1. Cron schedule fires background import or refresh job in `BackgroundJobEngine`.
  2. If transient database error occurs, worker captures exception, sets status to `RETRY`, and applies exponential backoff with jitter.
  3. If retries exhaust, job transitions to `FAILED` and dispatches notification to workspace admins.
- **Audit Assessment**: **PASS**. Validated in `test_automation_orchestration.py`.

---

## 10. Journey J: Workspace → Collaboration → Sharing → Permissions
- **Trace**:
  1. Admin invites member with role `EDITOR` from `/workspaces/members`.
  2. Member receives token and accepts via `/invitations/accept`.
  3. Member comments on a dataset widget with an `@mention`.
  4. Mentioned user receives real-time notification in `/activity` and navigation badge.
  5. Resource access policies enforce granular permissions (e.g., blocking export if permission revoked).
- **Audit Assessment**: **PASS**. Tested in `test_collaboration.py` and `test_governance_rbac.py`.

