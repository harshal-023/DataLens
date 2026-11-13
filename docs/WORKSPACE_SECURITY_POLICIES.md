# DataLens – Workspace Security Policies Architecture

## 1. Overview
Workspace Security Policies provide organization administrators with centralized guardrails to enforce compliance constraints, limit public data exposure, and govern user onboarding.

---

## 2. Configurable Policy Parameters
- **`allow_public_share_links`** (Boolean, default `True`): Toggles whether members can generate unauthenticated external share links for dashboards and reports.
- **`max_share_link_days`** (Integer, default `30`): Enforces an upper limit on external share link expiration.
- **`restrict_external_sharing`** (Boolean, default `False`): Disallows generating external links entirely.
- **`restrict_report_downloads`** (Boolean, default `False`): Disables PDF/DOCX/XLSX downloads.
- **`restrict_dataset_exports`** (Boolean, default `False`): Prevents raw CSV exports from datasets.
- **`max_session_hours`** (Integer, default `24`): Enforces maximum continuous session lifetime before re-authentication is required.
- **`allowed_invitation_domains`** (JSON Array, default `[]`): Allowlist of permitted email domains for workspace invitations (e.g., `["acme.corp", "subsidiary.com"]`).
- **`custom_roles_enabled`** (Boolean, default `True`): Toggles whether custom roles can be defined in this workspace.
- **`audit_retention_days`** (Integer, default `90`): Configures historical audit log retention period.

---

## 3. API Endpoints
- `GET /api/v1/workspace-security`: Fetch current workspace security policies.
- `PUT /api/v1/workspace-security`: Update workspace security policies.

