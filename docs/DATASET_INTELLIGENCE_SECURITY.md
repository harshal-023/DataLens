# Dataset Intelligence Security, RBAC & Isolation Controls

## 1. Security Invariants

1. **No Code Execution via Formulas:**
   The metric engine strictly enforces AST parsing via `SafeFormulaValidator`. The Python execution constructs `eval()`, `exec()`, `__import__`, `lambda`, and `os` are completely blocked and cannot execute.
2. **Untrusted Metadata Handling:**
   All uploaded column names and dataset metadata are treated as untrusted data strings. Identifiers are sanitized via `re.match(r"^[a-zA-Z0-9_]+$", name)` before injection into SQL queries, eliminating SQL injection risks.
3. **Zero Raw Data Cloud Egress:**
   Profiling metrics, aggregates, and statistical summaries are kept local. The AI Context Builder strictly forbids transmitting raw dataset records to external AI providers.
4. **Local-Only AI Enforcement:**
   Datasets tagged `CONFIDENTIAL` or `RESTRICTED`, or workspaces with `cloud_ai_permitted = False`, strictly block Cloud Gemini calls and cascade to Local Ollama or the Deterministic Engine.

---

## 2. Granular Role-Based Access Control (RBAC)

| Action | Allowed Roles | Endpoint / Service |
| :--- | :--- | :--- |
| **View Intelligence & Profiles** | Owner, Admin, Editor, Viewer | `GET /api/v1/datasets/{id}/intelligence` |
| **Trigger Profiling Run** | Owner, Admin, Editor | `POST /api/v1/datasets/{id}/intelligence/profile` |
| **Edit / Confirm Column Semantics** | Owner, Admin, Editor | `PATCH /api/v1/datasets/{id}/columns/semantics/{col}` |
| **Discover / Confirm Relationships** | Owner, Admin, Editor | `POST /api/v1/datasets/{id}/relationships/discover` |
| **Edit Business Context** | Owner, Admin, Editor | `PATCH /api/v1/datasets/{id}/business-context` |
| **Create / Update Metrics** | Owner, Admin, Editor | `POST /api/v1/metrics`, `PATCH /api/v1/metrics/{id}` |
| **Delete Metrics** | Owner, Admin | `DELETE /api/v1/metrics/{id}` |
| **Calculate Metric Preview** | Owner, Admin, Editor, Viewer | `POST /api/v1/metrics/calculate` |

---

## 3. Workspace Isolation Guarantees
- All queries filtering `ColumnSemanticMapping`, `BusinessContext`, `MetricDefinition`, and `DatasetRelationship` require `workspace_id` verification matching the authenticated user's active workspace session.
- Cross-workspace relationship discovery is strictly prohibited: the discovery engine scans only datasets belonging to the caller's authorized workspace.

