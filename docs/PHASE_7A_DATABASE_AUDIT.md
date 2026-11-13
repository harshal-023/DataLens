# Phase 7A: Database, Storage & Persistence Audit

## 1. Relational Persistence: PostgreSQL
DataLens utilizes PostgreSQL as its primary transactional and metadata store.
- **ORM**: SQLAlchemy 2.0 (asyncio with `asyncpg` driver).
- **Migration Framework**: Alembic.
- **Current Migration Head**: `20261112_0016` (verified clean head).
- **Total Relational Tables**: **69 tables** registered in `Base.metadata.tables`.

### Migration History (16 Migrations)
1. `20261111_0001_initial_schema`: Users, workspaces, initial dataset schemas.
2. `20261111_0002_auth_and_workspaces`: Workspace memberships, sessions, password reset tokens.
3. `20261111_0003_dataset_storage`: Parquet file storage keys, dataset versions.
4. `20261111_0004_prompt_lab`: Prompt templates, versions, test cases, evaluation runs.
5. `20261111_0005_advanced_analytics`: Model runs, anomaly, forecast, and segmentation results.
6. `20261111_0006_interactive_dashboards`: Dashboards, widgets, grid layouts, filters.
7. `20261111_0007_data_transformation`: Pipelines, steps, execution runs.
8. `20261111_0008_automated_business_reporting`: Business reports, templates, runs, schedules.
9. `20261112_0009_external_data_sources`: Connections, imports, refresh configs, metadata.
10. `20261112_0010_collaboration_sharing`: Comments, shares, notifications, activities.
11. `20261112_0011_enterprise_governance_rbac_audit`: Custom roles, policies, audit logs.
12. `20261112_0012_automation_orchestration`: Background jobs, job schedules, workflow DAGs.
13. `20261112_0013_unified_ai_architecture`: AI privacy policies, local/cloud routing settings.
14. `20261112_0014_dataset_intelligence_semantic_layer`: Semantic mappings, metrics, relationships.
15. `20261112_0015_conversational_analytics_engine`: NLA sessions, messages, saved analyses.
16. `20261112_0016_ai_business_analyst`: Business insights, evidence, assessments, assignments, runs.

### Integrity & Foreign Key Isolation
- All workspace-owned resources enforce foreign key constraints pointing to `workspaces(id)` with `ON DELETE CASCADE`.
- Composite indexes exist on `(workspace_id, created_at)` for high-throughput activity and audit log filtering.
- Unique constraints enforce deduplication (e.g., `(workspace_id, name)` on datasets and custom roles).

---

## 2. Columnar Analytical Storage: DuckDB & Parquet
DataLens utilizes a dual-engine storage model:
1. **PostgreSQL**: Stores relational metadata, user identities, permissions, dashboards, and audit logs.
2. **Parquet & DuckDB**: Stores dataset row data and executes analytical aggregations.
   - **Storage Format**: Standard Apache Parquet with Snappy compression.
   - **Location**: Storage paths are keyed by `datasets/{workspace_id}/{dataset_id}/{version_number}/data.parquet`.
   - **Query Engine**: DuckDB executes zero-copy queries against Parquet files via Python bindings.
   - **Privacy Isolation**: Queries against Parquet are executed with parameters compiled through AST validators, preventing SQL injection or filesystem traversal.

---

## 3. Background Job Persistence & Schedulers
- Background jobs are stored in `background_jobs` and `job_executions` tables in PostgreSQL.
- State machine tracks `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.
- Crash-recovery scans identify orphaned `RUNNING` jobs on worker startup and transition them to `RETRY` or `FAILED`.

