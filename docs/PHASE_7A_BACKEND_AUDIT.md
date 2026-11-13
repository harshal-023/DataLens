# Phase 7A: Backend Architecture, API & Service Audit

## 1. FastAPI Application Structure
The DataLens backend is built on **FastAPI (Python 3.13 / SQLAlchemy 2.0 Async / asyncpg / DuckDB / PyArrow)**. The primary application factory `create_application()` in `backend/app/main.py` registers:
- Structured JSON logging (`app.core.logging`).
- Centralized exception handlers for `AppException`, `ValidationError`, and unhandled HTTP exceptions.
- CORS middleware with strict origin allowlist validation.
- Lifespan context manager gracefully disposing of database connection pools on shutdown.
- All API routers mounted under `/api/v1` via `app.api.v1.router.api_v1_router`.

---

## 2. API Router & Endpoint Group Inventory

The backend exposes **263 total endpoints** across **23 resource groups**:

| Group | Router Module | Total Endpoints | Key Capabilities | Frontend Integration Status |
|---|---|---|---|---|
| **AI** | `endpoints/ai.py` | 9 | Intent classification, Ask Your Data, text explanation, Ollama model list, privacy policy config, provider status. | **CONNECTED** (via `aiService.ts` and `SettingsPage.tsx`) |
| **ANALYTICS** | `endpoints/analytics.py` | 9 | DuckDB query execution, historical runs, conversational follow-up, saved analyses CRUD. | **CONNECTED** (via `analyticsEngine.ts` and `AskYourData.tsx`) |
| **AUDIT-LOGS** | `endpoints/governance.py` | 2 | Immutable audit log retrieval, CSV/JSON audit export with integrity hash verification. | **CONNECTED** (via `governanceService.ts`) |
| **AUTH** | `endpoints/auth.py` | 9 | Register, login, refresh, logout, logout-all, password reset request/confirm, current user (`/me`). | **CONNECTED** (via `AuthContext.tsx` and `AuthPages.tsx`) |
| **AUTOMATION** | `endpoints/automation.py` | 20 | Background jobs, execution logs, retry, cancel, job schedules, workflow DAGs, trigger, validate. | **CONNECTED** (via `automationService.ts` and `DataAutomationPage.tsx`) |
| **BUSINESS-ANALYST** | `endpoints/business_analyst.py` | 15 | Executive overview, trends, anomalies, risks, opportunities, run trigger, status patching, comments, assignments, schedules. | **CONNECTED** (via `businessAnalystService.ts` and `BusinessAnalystCenter.tsx`) |
| **COMMENTS** | `endpoints/comments.py` | 6 | Threaded comment list, creation, editing, deletion, reopen, resolve, @mention notifications. | **CONNECTED** (via `collaborationService.ts`) |
| **CONNECTIONS** | `endpoints/connections.py` | 20 | Connector list, OAuth endpoints, connection test, discovery, table preview, import jobs, refresh configs. | **CONNECTED** (via `dataSourceService.ts` and `DataSourcesOverview.tsx`) |
| **DASHBOARDS** | `endpoints/dashboards.py` | 22 | Dashboard CRUD, duplication, exports, layout updates, widget CRUD, filter management. | **CONNECTED** (via `dashboardService.ts` and `DashboardEditor.tsx`) |
| **DATASETS** | `endpoints/datasets.py` | 15 | File upload, chunked ingestion, dataset CRUD, version history, column profiling, download, data preview. | **CONNECTED** (via `storageService.ts` and `DataStudio.tsx`) |
| **EXPERIMENTS** | `endpoints/experiments.py` | 10 | Prompt Lab experiments, multi-model evaluation, test runs, benchmark comparisons. | **CONNECTED** (via `ExperimentDetail.tsx`) |
| **GOVERNANCE** | `endpoints/governance.py` | 13 | Workspace security policies, custom roles, resource access policies, session management. | **CONNECTED** (via `governanceService.ts` and `EnterpriseSecurityPage.tsx`) |
| **HEALTH** | `endpoints/health.py` | 3 | Liveness `/health`, readiness `/ready`, detailed system diagnostic checks. | **CONNECTED** (Used by monitoring and startup probes) |
| **INTELLIGENCE** | `endpoints/intelligence.py` | 18 | Statistical profiling, semantic mappings, relationship discovery, business context, KPI suggestions. | **CONNECTED** (via `intelligenceService.ts` and `DatasetDetail.tsx`) |
| **INVITATIONS** | `endpoints/invitations.py` | 4 | Workspace invitations list, creation, resend, revoke, public acceptance. | **CONNECTED** (via `WorkspaceMembers.tsx` and `AcceptInvitation.tsx`) |
| **METRICS** | `endpoints/metrics.py` | 10 | Semantic metric definitions, AST formula validation, approval workflow, calculation on Parquet. | **CONNECTED** (via `intelligenceService.ts`) |
| **ML** | `endpoints/ml.py` | 7 | Statistical anomaly detection, time-series forecasting, KMeans customer clustering, ML reports. | **CONNECTED** (via `AdvancedAnalyticsPage.tsx`) |
| **NOTIFICATIONS** | `endpoints/notifications.py` | 8 | User notifications, unread count badge, mark read, preferences, SSE live stream. | **CONNECTED** (via `Navbar.tsx` and `collaborationService.ts`) |
| **PERMISSIONS** | `endpoints/governance.py` | 4 | Canonical permission catalog, resource permission rules. | **CONNECTED** (via `governanceService.ts`) |
| **PROMPTS** | `endpoints/prompts.py` | 12 | Prompt template registry, versioning, restore, variable extraction, sandbox execution. | **CONNECTED** (via `PromptLabOverview.tsx`) |
| **REPORTS** | `endpoints/reports.py` | 26 | Business report CRUD, templates, multi-format run execution (PDF/DOCX/XLSX/CSV), downloads, share links. | **CONNECTED** (via `businessReportService.ts` and `ReportsLibrary.tsx`) |
| **ROLES** | `endpoints/governance.py` | 6 | Custom role creation, duplication, assignment to members, permission grants. | **CONNECTED** (via `EnterpriseSecurityPage.tsx`) |
| **SECURITY-EVENTS**| `endpoints/governance.py` | 2 | Security event audit trail, investigation status update. | **CONNECTED** (via `EnterpriseSecurityPage.tsx`) |
| **SESSIONS** | `endpoints/governance.py` | 3 | Active user sessions list, revoke specific session, revoke all other sessions. | **CONNECTED** (via `EnterpriseSecurityPage.tsx` and `SettingsPage.tsx`) |
| **SHARED** | `endpoints/shares.py` | 2 | Public token access for shared dashboards and password-protected report downloads. | **CONNECTED** (Public share links) |
| **TRANSFORMATIONS**| `endpoints/transformations.py`| 12 | Pipeline CRUD, step reordering, AST formula validation, pipeline preview, derived dataset run. | **CONNECTED** (via `transformationService.ts` and `DataPreparationEditor.tsx`) |
| **USERS** | `endpoints/users.py` | 1 | Update user profile, full name, avatar. | **CONNECTED** (via `SettingsPage.tsx`) |
| **WORKSPACES** | `endpoints/workspaces.py` | 13 | Workspace CRUD, activity feed, member roles, invitations. | **CONNECTED** (via `WorkspaceMembers.tsx` and `WorkspaceActivityPage.tsx`) |

---

## 3. Disconnected / Duplicate Endpoint Analysis
1. **Duplicate Duplication Route**:
   - In `dashboards.py`, endpoint `/api/v1/dashboards/{dashboard_id}/duplicate` is declared twice in router mounting with identical functionality. While harmless, one route handler is redundant.
2. **Phase 1 Legacy Fallback Endpoints**:
   - Legacy endpoints `/api/v1/reports` and `/api/v1/reports/business` coexist. `/api/v1/reports` supports the original Phase 1 simple report runs, while `/api/v1/reports/business` supports Phase 4D executive enterprise reports. Both remain functional for backward compatibility.
3. **Frontend Connection Completeness**:
   - 100% of major feature categories have direct service clients in `src/services/` that actively call the respective backend endpoints.

