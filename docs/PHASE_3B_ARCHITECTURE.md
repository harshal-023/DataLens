# DataLens — Phase 3B Architecture: Prompt Lab

## 1. Current Architecture Summary

### Backend Stack
- **Framework:** FastAPI with Pydantic v2
- **Database:** PostgreSQL 18 via SQLAlchemy 2.x async + asyncpg
- **Migrations:** Alembic (head: `20261111_0003`)
- **Auth:** JWT access/refresh tokens, Argon2id, workspace RBAC (owner/admin/editor/viewer)
- **AI:** Provider abstraction (`AIProvider` → `OpenAIProvider` / `DisabledAIProvider`), factory pattern
- **Analytics:** DuckDB-based deterministic engine
- **Storage:** Local filesystem with Parquet (PyArrow)

### Frontend Stack
- **Framework:** React 18 + TypeScript + Vite
- **Styling:** Tailwind CSS with custom design tokens
- **Charts:** Recharts
- **Icons:** lucide-react
- **HTTP:** Axios with JWT interceptor
- **State:** React Context (Auth, Workspace, Toast) + local state

### Existing Models
- User, Workspace, WorkspaceMembership, Dataset, DatasetVersion, AnalysisRun, Report

### Existing AI Services
- `AIProvider` (abstract), `OpenAIProvider`, `DisabledAIProvider`
- `AIProviderFactory.create_provider(settings)`
- `AIAnalyticsOrchestrator` (Ask Your Data pipeline)
- `PlanValidator` (schema-aware plan validation)

### Existing Prompt Lab Frontend
- Placeholder `PromptLab.tsx` with "Coming Soon" card
- Placeholder `ExperimentDetail.tsx` with "Coming Soon" message
- Sidebar navigation entry already exists at `/prompt-lab`
- Route `/prompt-lab/experiments/:id` already registered

---

## 2. Proposed Architecture

### 2.1 Database Entities

```
┌─────────────────────┐     ┌──────────────────────┐
│   prompt_templates   │────▶│   prompt_versions    │
│                     │  1:N │                      │
│ id (UUID PK)        │     │ id (UUID PK)          │
│ workspace_id (FK)   │     │ prompt_id (FK)        │
│ name                │     │ version_number        │
│ description         │     │ system_prompt         │
│ category            │     │ user_prompt_template  │
│ tags (JSON)         │     │ variables (JSON)      │
│ created_by (FK)     │     │ model_config (JSON)   │
│ created_at          │     │ change_description    │
│ updated_at          │     │ created_by (FK)       │
│ is_archived         │     │ created_at            │
└─────────────────────┘     └──────────────────────┘
                                      │
                                      │ referenced by
                                      ▼
┌─────────────────────┐     ┌──────────────────────┐
│    experiments       │────▶│  experiment_runs     │
│                     │  1:N │                      │
│ id (UUID PK)        │     │ id (UUID PK)          │
│ workspace_id (FK)   │     │ experiment_id (FK)    │
│ name                │     │ prompt_version_id(FK) │
│ description         │     │ test_case_id (FK)     │
│ prompt_id (FK)      │     │ rendered_prompt       │
│ version_ids (JSON)  │     │ response_text         │
│ model_config (JSON) │     │ provider              │
│ status              │     │ model                 │
│ created_by (FK)     │     │ status                │
│ created_at          │     │ input_tokens          │
│ updated_at          │     │ output_tokens         │
│                     │     │ latency_ms            │
└─────────────────────┘     │ error_message         │
         │                  │ created_at            │
         │                  └──────────────────────┘
         │ 1:N                        │
         ▼                            │ 1:N
┌─────────────────────┐     ┌──────────────────────┐
│    test_cases        │     │  evaluation_results  │
│                     │     │                      │
│ id (UUID PK)        │     │ id (UUID PK)          │
│ experiment_id (FK)  │     │ run_id (FK)           │
│ name                │     │ metric_name           │
│ variables (JSON)    │     │ score                 │
│ expected_output     │     │ max_score             │
│ created_at          │     │ evaluation_method     │
└─────────────────────┘     │ explanation           │
                            │ evaluated_by_model    │
                            │ created_at            │
                            └──────────────────────┘
```

### 2.2 API Design

All endpoints under `/api/v1/` with JWT authentication and workspace RBAC.

**Prompt Library:**
| Method | Path | Description |
|--------|------|-------------|
| POST | /prompts | Create prompt template |
| GET | /prompts | List prompts (workspace, search, category, tags) |
| GET | /prompts/{id} | Get prompt details |
| PATCH | /prompts/{id} | Update prompt metadata |
| POST | /prompts/{id}/duplicate | Duplicate prompt |
| DELETE | /prompts/{id} | Archive prompt |

**Prompt Versions:**
| Method | Path | Description |
|--------|------|-------------|
| POST | /prompts/{id}/versions | Create new version |
| GET | /prompts/{id}/versions | List version history |
| GET | /prompts/{id}/versions/{vid} | Get specific version |
| POST | /prompts/{id}/versions/{vid}/restore | Restore (creates new version from old) |

**Playground:**
| Method | Path | Description |
|--------|------|-------------|
| POST | /prompts/execute | Execute prompt with variables |

**Experiments:**
| Method | Path | Description |
|--------|------|-------------|
| POST | /experiments | Create experiment |
| GET | /experiments | List experiments |
| GET | /experiments/{id} | Get experiment details |
| POST | /experiments/{id}/run | Run experiment |
| POST | /experiments/{id}/cancel | Cancel experiment |
| GET | /experiments/{id}/results | Get execution results |

**Evaluations:**
| Method | Path | Description |
|--------|------|-------------|
| POST | /experiments/{id}/evaluate | Evaluate experiment results |
| GET | /experiments/{id}/evaluations | Get evaluations |

**Comparison:**
| Method | Path | Description |
|--------|------|-------------|
| GET | /experiments/{id}/comparison | Get version comparison analytics |

### 2.3 Frontend Page Structure

```
/prompt-lab
├── Prompt Library (default view)
│   ├── Search/filter bar
│   ├── Category tabs
│   └── Prompt cards grid
├── /prompt-lab/prompts/:id
│   ├── Prompt Editor (system + user template + variables)
│   ├── Version History tab
│   └── Playground tab
├── /prompt-lab/experiments
│   ├── Experiment list
│   └── Create experiment modal
├── /prompt-lab/experiments/:id
│   ├── Experiment overview
│   ├── Test cases tab
│   ├── Results tab
│   ├── Evaluations tab
│   └── Comparison dashboard tab
```

### 2.4 Experiment Lifecycle

```
Created → Pending → Running → Completed/Failed/Cancelled
                      │
                      ├── For each (version × test_case):
                      │     1. Render prompt template with test variables
                      │     2. Execute via AIProvider
                      │     3. Record response, tokens, latency
                      │     4. Store as ExperimentRun
                      │
                      └── On completion: status → Completed
                          On any failure: status → Failed (partial results preserved)
                          On cancel: status → Cancelled
```

### 2.5 Evaluation Methodology

**Deterministic Metrics (computed locally):**
- Exact match against expected output
- Keyword presence check
- JSON validity / schema compliance
- Response length bounds
- Required field completeness
- Execution success rate

**Model-Assisted Metrics (via AI provider, clearly labeled):**
- Relevance (1-5 scale)
- Instruction following (1-5 scale)
- Factual consistency (1-5 scale)
- Completeness (1-5 scale)
- Clarity (1-5 scale)

All model-assisted scores are labeled as "AI-Judged" in the UI.

### 2.6 Security Considerations

- All prompt/experiment endpoints require JWT authentication
- Workspace isolation enforced on every query
- RBAC: Viewers can read prompts/experiments; Editors+ can create/modify
- Immutable versions: once created, version content cannot be modified
- Variable rendering is text substitution only — no code execution
- Provider API keys never exposed to frontend
- Model-assisted evaluation clearly distinguished from deterministic
- Experiment cancellation sets status without corrupting partial results

---

## 3. Implementation Stages

| Stage | Scope | Dependencies |
|-------|-------|-------------|
| 1 | Prompt Library (models, API, frontend) | None |
| 2 | Prompt Versioning (immutable versions, history, comparison) | Stage 1 |
| 3 | Prompt Playground (execution, metadata display) | Stage 2 |
| 4 | Experiment Management (lifecycle, test cases) | Stage 3 |
| 5 | Evaluation Engine (deterministic + model-assisted metrics) | Stage 4 |
| 6 | Prompt Experiment Analytics (comparison dashboard) | Stage 5 |
| 7 | Frontend Prompt Lab Experience (complete UI) | Stages 1-6 |
| 8 | Backend API finalization (all endpoints verified) | Stages 1-6 |
| 9 | Security verification | All stages |
| 10 | Testing | All stages |
| 11 | Documentation | All stages |

---

## 4. Alembic Migration Plan

New migration: `20261111_0004_prompt_lab.py`

Creates tables:
- `prompt_templates`
- `prompt_versions`
- `experiments`
- `test_cases`
- `experiment_runs`
- `evaluation_results`

All with proper foreign keys, indexes, and constraints.

