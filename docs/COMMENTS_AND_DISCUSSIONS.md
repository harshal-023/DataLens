# DataLens – Comments, Discussions & @Mentions Architecture

## 1. Overview
The Comments & Discussions system transforms DataLens into an interactive collaborative workspace, enabling team members to hold analytical discussions directly alongside dashboards and business reports.

---

## 2. Core Features
- **Threaded Replies**: Multi-level discussion threads supporting root discussions and nested reply responses.
- **@Mention Extraction**: Automatically identifies `@username` or `@email` tokens within comment text, searches matching workspace members, and dispatches in-app and email notifications.
- **Discussion Resolution**: Mark discussion threads as resolved or reopen them when analytical questions require further review.
- **Security & XSS Prevention**: All comment text is HTML-escaped using Python's `html.escape()` and validated against cross-site scripting attack vectors.
- **Soft Deletion**: Author or admin comment deletion flags `is_deleted = True` while preserving audit integrity.

---

## 3. Data Model (`Comment`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `workspace_id` | UUID | Owning workspace |
| `resource_type` | String | `dashboard` or `report` |
| `resource_id` | UUID | Targeted dashboard or report ID |
| `parent_id` | UUID | Null for root comments; parent UUID for replies |
| `author_id` | UUID | Comment author user ID |
| `content` | Text | Sanitized comment text |
| `mentions` | JSONB | List of mentioned username tokens |
| `is_resolved` | Boolean | True if root thread has been resolved |
| `resolved_by_id` | UUID | User who resolved the thread |
| `resolved_at` | DateTime | Timestamp of resolution |
| `is_deleted` | Boolean | Soft-deletion flag |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last edit timestamp |

---

## 4. API Endpoints
- `GET /api/v1/comments`: List threaded comments for a dashboard or report.
- `POST /api/v1/comments`: Post a new root comment or reply.
- `PATCH /api/v1/comments/{comment_id}`: Edit comment content (author only).
- `DELETE /api/v1/comments/{comment_id}`: Delete comment (author or admin).
- `POST /api/v1/comments/{comment_id}/resolve`: Mark thread as resolved.
- `POST /api/v1/comments/{comment_id}/reopen`: Reopen resolved thread.

