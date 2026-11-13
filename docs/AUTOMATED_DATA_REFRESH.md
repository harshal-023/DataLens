# DataLens Phase 5D – Automated Data Source Refresh

---

## 1. Overview

The Automated Data Refresh subsystem integrates with all six Phase 5A external connectors:
1. **PostgreSQL Connector:** Full & incremental timestamp/ID watermark queries.
2. **MySQL Connector:** Full & incremental binary log/watermark queries.
3. **REST API Connector:** Full ingestion & pagination/cursor-based refresh.
4. **Google Sheets Connector:** Full worksheet extraction & cell change tracking.
5. **MongoDB Connector:** Full collection dump & ObjectId/timestamp delta queries.
6. **S3-Compatible Storage:** Object ingestion & ETag/modified timestamp checks.

---

## 2. Refresh Modes & Integrity Safeguards

### Full Refresh
Re-queries the target resource, builds a complete Parquet representation, profiles the schema, and creates a new immutable `DatasetVersion` pointing to the updated data.

### Incremental Refresh
Queries records where `watermark_column > last_watermark_value`. Appends the new delta to existing immutable Parquet partitions and records the updated high watermark.

### Prohibition on Silent Degradation
If incremental refresh is requested without a valid `watermark_column` or if change tracking validation fails:
- The engine **NEVER** silently falls back to a full dataset import.
- The job fails with `ErrorClassification.VALIDATION`.
- An alert is dispatched requiring explicit administrative reconfiguration.

