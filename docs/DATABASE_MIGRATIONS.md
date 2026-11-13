]
# DataLens — Database Migrations Guide

DataLens manages its PostgreSQL schema versions using **Alembic** with asynchronous SQLAlchemy models.

---

## 1. Migration History

The schema is partitioned across incremental migrations:

| Revision ID | Description | Created Tables / Columns |
| :--- | :--- | :--- |
| `20261111_0001` | Initial core schema (Phase 2A) | `users`, `workspaces`, `workspace_memberships`, `datasets`, `dataset_versions`, `analysis_runs`, `reports` |
| `20261111_0002` | Authentication & Workspaces (Phase 2B) | `refresh_sessions`, `password_reset_tokens`, `workspace_invitations` |
| `20261111_0003` | Dataset enhancements (Phase 2C/2D) | Soft archival `datasets.is_archived`, version key `dataset_versions.original_storage_key` |

---

## 2. Common Migration Commands

Always run from `backend/`:

```powershell
cd "d:\PE CP\backend"

# 1. Inspect current migration revision in database
.\.venv\Scripts\python.exe -m alembic current

# 2. Inspect migration history tree
.\.venv\Scripts\python.exe -m alembic history

# 3. Upgrade to latest schema (head)
.\.venv\Scripts\python.exe -m alembic upgrade head

# 4. Generate upgrade SQL offline (dry-run without connecting)
.\.venv\Scripts\python.exe -m alembic upgrade head --sql

# 5. Generate downgrade SQL offline
.\.venv\Scripts\python.exe -m alembic downgrade 20261111_0003:base --sql
```

---

## 3. Creating New Migrations

When models in `app/models/` change:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe_schema_change"
```

Inspect the generated file under `backend/alembic/versions/` and ensure safe defaults before applying.

