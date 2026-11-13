# DataLens — Prompt Versioning & Immutability

## 1. Principles of Immutability

Prompt engineering requires reproducible scientific experimentation. Overwriting a prompt in place breaks experiment provenance and distorts historical benchmarks.

In DataLens:
1. **Never Overwrite**: Published prompt versions in `prompt_versions` are immutable.
2. **Explicit Revisions**: Any modification to system instructions, user templates, variable definitions, or model parameter snapshots creates an incremented version ($v_1 \to v_2 \to v_3$).
3. **Provable Experiment Provenance**: Experiment runs store foreign keys directly to the exact `prompt_version_id` used during execution.

---

## 2. Version Entity Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique prompt version identifier. |
| `prompt_id` | UUID (FK) | Reference to parent prompt template. |
| `version_number` | Integer | Sequentially incrementing revision number. |
| `system_prompt` | Text | System directives and constraints. |
| `user_prompt_template` | Text | Template containing variable placeholders. |
| `variables` | JSONB Array | List of variable schemas (`name`, `required`, `description`). |
| `model_config_snapshot`| JSONB | Frozen model settings (`provider`, `model`, `temperature`, `max_tokens`). |
| `change_description` | String(500) | Human-readable explanation of changes in this revision. |
| `created_by` | UUID (FK) | User who created this revision. |
| `created_at` | DateTime (UTC) | Version creation timestamp. |

**Constraint**: `UniqueConstraint("prompt_id", "version_number")` guarantees monotonic version uniqueness per prompt.

---

## 3. Side-by-Side Comparison & Restoration

### Version Comparison (`GET /api/v1/prompts/{prompt_id}/compare?version_a=...&version_b=...`)
Performs structural diffing across:
- `system_prompt_diff`: Changes in system persona or constraints.
- `user_prompt_diff`: Changes in user template text and phrasing.
- `variables_diff`: Added, removed, or modified variables.
- `model_config_diff`: Changes in temperature, model, or token limits.

### Safe Restoration (`POST /api/v1/prompts/{prompt_id}/versions/{version_id}/restore`)
Restoring an older version creates a **new forward revision** containing the historical version's contents. For instance, restoring $v_1$ when the latest is $v_3$ creates $v_4$ with $v_1$'s content and description: `"Restored from Version 1"`. Historical records $v_1$, $v_2$, and $v_3$ remain intact.

