# DataLens – Workspace Team Collaboration Platform

## 1. Overview & Objective
DataLens Phase 5B introduces a complete team collaboration layer on top of workspaces, enabling cross-functional analytical teams to work together securely with fine-grained access control, role hierarchies, and real-time communication.

---

## 2. Workspace Membership & Role Hierarchy
Workspaces enforce a 4-tier Role-Based Access Control (RBAC) model:

| Role | Permissions & Capabilities |
| :--- | :--- |
| **Owner** | Full workspace authority. Can rename/delete workspace, manage billing, promote/demote members, transfer ownership, and perform all Admin/Editor actions. Cannot be removed unless ownership is transferred. |
| **Admin** | Member invitation management, role updates (up to Admin), connection credential configuration, dashboard/report deletion, and discussion moderation. |
| **Editor** | Upload datasets, create transformation pipelines, build & edit dashboards, create reports, share resources, write comments & replies. |
| **Viewer** | Read-only access to datasets, dashboards, and reports within the workspace. Can participate in discussions and view activity feeds. |

---

## 3. Collaboration Data Models
- **`WorkspaceMembership`**: Connects `users` to `workspaces` with an assigned `role` and `joined_at` timestamp.
- **`ResourceShare`**: Explicit resource-level sharing granting granular `viewer` or `editor` permissions to individual users on specific dashboards or reports.
- **`ShareAccessToken`**: Cryptographically secure URL-safe tokens enabling controlled external access with optional password hashing, expiration timestamps, and download restrictions.

---

## 4. REST API Endpoints
- `GET /api/v1/workspaces/{workspace_id}/members`: Lists active members with roles and join dates.
- `PATCH /api/v1/workspaces/{workspace_id}/members/{user_id}`: Promotes or demotes member roles (Owner/Admin only).
- `DELETE /api/v1/workspaces/{workspace_id}/members/{user_id}`: Removes member from workspace or allows a member to leave. Last owner removal is strictly blocked.

