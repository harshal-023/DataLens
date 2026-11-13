# DataLens – Workspace Activity & Audit Feed Architecture

## 1. Overview
The Workspace Activity Feed provides an immutable, chronological audit trail of all significant operational, collaborative, and analytical events occurring within a workspace.

---

## 2. Event Types & Tracing
The activity logger records events across all platform subsystems:
- **Team & Permissions**: `invitation_sent`, `member_joined`, `member_role_changed`, `member_removed`
- **Dashboards**: `dashboard_created`, `dashboard_updated`, `dashboard_shared`, `dashboard_share_revoked`, `dashboard_duplicated`
- **Reports**: `report_created`, `report_generated`, `report_shared`, `report_share_revoked`
- **Discussions**: `comment_added`, `discussion_resolved`, `discussion_reopened`
- **Data Integrations**: `connection_created`, `dataset_imported`, `dataset_refreshed`

---

## 3. Secret Masking & Sanitization
To guarantee zero sensitive data exposure in audit feeds:
- `CollaborationService.log_activity` evaluates all keys in `metadata_snapshot`.
- Any key matching sensitive keywords (`password`, `token`, `secret`, `key`, `credential`, `auth`, `cert`, `private`) has its value redacted to `"••••••••"`.
- Summaries are truncated to 500 characters maximum.

---

## 4. API Endpoints
- `GET /api/v1/workspaces/{workspace_id}/activity`: Retrieve paginated activity feed with optional query filters:
  - `actor_id` (UUID): Filter by specific team member.
  - `resource_type` (String): Filter by resource (`dashboard`, `report`, `dataset`, `invitation`, etc.).
  - `event_type` (String): Filter by specific event type.
  - `page` & `page_size`: Pagination parameters.

