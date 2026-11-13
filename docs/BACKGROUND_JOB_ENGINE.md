# DataLens Phase 5D – Centralized Background Job Engine

---

## 1. Engine Overview

The DataLens Background Job Engine is a high-throughput, database-backed background execution and orchestration service implemented natively on top of PostgreSQL.

It eliminates external queue infrastructure dependencies (such as Redis or Celery) while guaranteeing:
- Multi-worker concurrency with zero race conditions.
- Strict atomic claiming via PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`.
- Process restart resilience (persistent DB state).
- Distributed lease heartbeats and stale worker crash recovery.
- End-to-end execution tracking, progress streaming, and structured JSON logs.

---

## 2. Supported Job Types

| Job Type Key | Description | Target Subsystem |
|---|---|---|
| `data_import` | External data ingestion from external databases, REST APIs, or cloud object storage. | `ImportEngine.execute_import` |
| `dataset_refresh` | Full dataset replacement refresh. | `ImportEngine.execute_import` |
| `incremental_refresh` | Watermark-based delta sync without full dataset re-ingestion. | `ImportEngine.execute_import` |
| `pipeline_execution` | Phase 4B transformation pipeline run, producing derived datasets. | `TransformationService.run_pipeline` |
| `data_validation` | Pre-materialization data quality gates (schema drift, nulls, duplicates). | `DataQualityService.validate_dataset_records` |
| `dataset_materialization` | Immutable Parquet storage commitment and version tagging. | `DatasetService` / Parquet Storage |
| `report_generation` | Automated report compilation with PDF/XLSX generation. | `BusinessReportService.generate_report_run` |
| `report_delivery` | Report delivery via email or workspace notifications. | `EmailDeliveryService` / Notifications |
| `workflow` | Complete end-to-end multi-step DAG orchestration run. | `WorkflowDAGService` |

---

## 3. Atomic Job Claiming Algorithm

```sql
SELECT id FROM background_jobs
WHERE status = 'QUEUED' AND scheduled_at <= NOW()
ORDER BY priority DESC, scheduled_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

When claimed:
1. `status` transitions atomically to `RUNNING`.
2. `worker_id` is assigned the unique worker identifier (e.g. `worker-host-pid`).
3. `started_at` and `heartbeat_at` are set to `NOW()`.
4. A corresponding `JobExecution` row is created tracking `attempt_number = retry_count + 1`.

---

## 4. Job Cancellation & Idempotency

- **Idempotency Key:** Background jobs accept a unique `idempotency_key` (e.g., `sched_<id>_<timestamp>`). If a job with the same key already exists in the workspace, the existing job is returned without creating duplicate entries.
- **Atomic Cancellation:** Calling `BackgroundJobService.cancel_job` immediately sets status to `CANCELLED` and finalizes the active execution attempt.

