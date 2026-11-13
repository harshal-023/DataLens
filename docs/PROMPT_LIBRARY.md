# DataLens — Prompt Library Documentation

## 1. Overview

The **Prompt Library** in DataLens provides an enterprise repository for creating, managing, categorizing, and maintaining prompt templates for AI-powered business intelligence operations.

Prompt Lab is completely decoupled from Ask Your Data. While Ask Your Data is tailored for natural language querying over specific datasets, Prompt Lab provides an engineering environment to systematically design, version, test, and benchmark prompt strategies.

---

## 2. Prompt Template Schema & Attributes

Each managed prompt template in `prompt_templates` maintains:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique prompt template identifier. |
| `workspace_id` | UUID (FK) | Enforces strict multi-tenant workspace isolation. |
| `name` | String(120) | User-facing title (e.g., *Executive KPI Summary Generator*). |
| `description` | String(500) | Detailed business objective and intended output scope. |
| `category` | String(50) | Categorical taxonomy for filtering and organization. |
| `tags` | JSONB Array | List of tag strings (e.g., `["kpi", "finance", "executive"]`). |
| `created_by` | UUID (FK) | User who authored the template. |
| `is_archived` | Boolean | Soft-deletion flag preserving historical experiment traces. |
| `created_at` | DateTime (UTC) | Creation timestamp. |
| `updated_at` | DateTime (UTC) | Last metadata update timestamp. |

### Supported Categories
- `Business Intelligence`
- `Data Analysis`
- `Summarization`
- `Classification`
- `Information Extraction`
- `Content Generation`
- `Custom`

---

## 3. Template Variables & Safe Rendering

Prompt templates support dynamic variable placeholders using double-curly syntax:
```text
Analyze the financial performance of {{company}} in {{region}} for Q{{quarter}}.
Highlight key variances exceeding {{threshold_percent}}%.
```

### Variable Invariants:
1. **Extraction**: `PromptTemplateEngine.extract_variables(template)` uses regex `\{\{([a-zA-Z0-9_]+)\}\}` to isolate unique placeholders in order.
2. **Missing Variable Enforcement**: `validate_and_render()` validates that all detected and required variables have provided values. If any required variable is unpopulated, execution is blocked with `MISSING_PROMPT_VARIABLES`.
3. **Prompt Injection Resistance**: Variables undergo safe string substitution without eval, shell execution, or system prompt override.

---

## 4. API Endpoints

- `POST /api/v1/prompts`: Create template + publish Version 1.
- `GET /api/v1/prompts`: List templates (search, category filter, tag filter).
- `GET /api/v1/prompts/{prompt_id}`: Full detail with latest version snapshot.
- `PATCH /api/v1/prompts/{prompt_id}`: Update metadata (name, description, tags, category). Does not mutate versions.
- `POST /api/v1/prompts/{prompt_id}/duplicate`: Clone template and initial version.
- `DELETE /api/v1/prompts/{prompt_id}`: Soft-archive template.

