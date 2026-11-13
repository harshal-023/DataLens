# DataLens – Interactive Dashboard Sharing & Duplication Platform

## 1. Overview
The Dashboard Sharing Engine enables analytical collaboration through three distinct mechanisms:
1. **Direct Member Shares**: Granting specific workspace members tailored Viewer or Editor permissions.
2. **Controlled Share Links**: Generating time-limited, password-protected, revocable links for external stakeholders with query capabilities.
3. **Dashboard Duplication**: Cloning an entire dashboard with its widget arrangements, layout configurations, and filters into any permitted workspace.

---

## 2. Controlled External Links Architecture
External share links allow stakeholders to view live dashboards without creating a DataLens account:
- **Revocability**: Links can be revoked instantly at any time by workspace administrators.
- **Expiration Policies**: Configurable durations (1 day, 7 days, 30 days, or indefinite). Expired links reject requests with code `EXPIRED_LINK`.
- **Password Protection**: Optional SHA-256 hashed password. Protected links require password verification before returning widget layout and query capabilities.
- **Download Restrictions**: The `allow_download` flag permits or restricts underlying CSV and report exports.
- **Audit Metrics**: Automatically increments `access_count` and updates `last_accessed_at` on every authenticated access.

---

## 3. Dashboard Duplication
Duplicating a dashboard deep-copies:
- The `Dashboard` record with a user-specified title (defaulting to `<Original> (Copy)`).
- All `DashboardWidget` records with identical visualization types, metrics, dimensions, and grid coordinates.
- All `DashboardFilter` records ensuring cross-filtering and drill-down behaviors remain intact.
- Emits a `dashboard_duplicated` audit event to `workspace_activity`.

---

## 4. API Endpoints
- `POST /api/v1/dashboards/{dashboard_id}/shares`: Add member share.
- `GET /api/v1/dashboards/{dashboard_id}/shares`: List member shares.
- `DELETE /api/v1/dashboards/{dashboard_id}/shares/{share_id}`: Revoke member share.
- `POST /api/v1/dashboards/{dashboard_id}/links`: Create controlled share link.
- `GET /api/v1/dashboards/{dashboard_id}/links`: List active share links.
- `DELETE /api/v1/dashboards/{dashboard_id}/links/{token_id}`: Revoke share link.
- `POST /api/v1/dashboards/{dashboard_id}/duplicate`: Duplicate dashboard to workspace.
- `POST /api/v1/shared/dashboards/{token}`: Resolve public shared dashboard.

