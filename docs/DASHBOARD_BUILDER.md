# DataLens — Interactive Dashboard Builder Guide

## Overview

The **Interactive Dashboard Builder** (Phase 4A) enables analysts, operations leads, and workspace owners to construct, layout, customize, and share interactive Business Intelligence dashboards directly within DataLens.

Key Capabilities:
- **Persistent Storage:** Stored in PostgreSQL with workspace multi-tenancy and RBAC.
- **DuckDB Performance:** All numerical calculations, aggregations, and trends run server-side against immutable Parquet data.
- **Flexible Grid:** 12-column responsive layout with drag-and-drop reordering and granular sizing controls.
- **Cross-Widget Filters:** Interactive filter bar dynamically updates connected widgets without full page reloads.
- **Multi-Format Export:** Export complete dashboards to branded PDF reports, multi-sheet Excel workbooks (XLSX), or CSV tables.

---

## Architecture & Workflows

### 1. Dashboard Lifecycle
- **Create:** Click `New Dashboard` from `/dashboards` or use `POST /api/v1/dashboards`.
- **Edit Mode:** Interactive grid where widgets can be resized, dragged, reconfigured, or deleted.
- **View / Presentation Mode:** Clean, distraction-free view designed for stakeholders and executives.
- **Duplication:** Clones the dashboard, all attached widgets, and filters with a single click.
- **Archival / Soft-Delete:** Dashboards can be archived or permanently purged.

### 2. Workspace Multi-Tenancy & Access Control
- **Owner & Admin:** Full dashboard management (create, update, reorder, duplicate, delete, export).
- **Editor:** Create, edit widgets, reorder layout, and export. Cannot delete dashboards.
- **Viewer:** View dashboards, toggle filters, and export. Read-only permissions enforced server-side.

### 3. Grid Sizing & Drag-and-Drop
- Built upon a **12-column responsive grid system**.
- Quick column width resizing (`W-` / `W+`) adjusts width between 3 and 12 columns.
- Row height adjustment (`H-` / `H+`) adjusts height blocks.
- Drag handle on each widget card allows intuitive rearrangement with automatic order assignment.

---

## REST API Reference

| Endpoint | Method | Role | Description |
| :--- | :---: | :---: | :--- |
| `/api/v1/dashboards` | `POST` | Owner, Admin, Editor | Create a new dashboard |
| `/api/v1/dashboards` | `GET` | Viewer+ | List workspace dashboards (paginated, searchable) |
| `/api/v1/dashboards/{id}` | `GET` | Viewer+ | Retrieve full dashboard detail with widgets & filters |
| `/api/v1/dashboards/{id}` | `PUT` | Owner, Admin, Editor | Update title, description, visibility, and layout |
| `/api/v1/dashboards/{id}/duplicate` | `POST` | Owner, Admin, Editor | Duplicate dashboard, widgets, and filters |
| `/api/v1/dashboards/{id}` | `DELETE` | Owner, Admin | Archive or permanently delete dashboard |
| `/api/v1/dashboards/{id}/layout` | `POST` | Owner, Admin, Editor | Batch update widget grid coordinates (`x`, `y`, `w`, `h`) |
| `/api/v1/dashboards/{id}/export` | `POST` | Viewer+ | Export dashboard to PDF, CSV, or XLSX |

