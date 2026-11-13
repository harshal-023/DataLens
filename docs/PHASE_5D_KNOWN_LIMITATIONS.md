# DataLens Phase 5D – Known Limitations & Future Architecture Considerations

---

## 1. Zero-Dependency Pure-Python Cron vs. Second-Level Precision

### Limitation
The built-in pure-Python cron parser evaluates standard 5-field UNIX expressions (`minute hour dom month dow`). It does not support non-standard 6-field second-level precision cron syntax (e.g. `*/5 * * * * *`).

### Boundary
- Business intelligence automations (data refreshes, ETL pipelines, reports) operate on minute-level granularity. Sub-minute scheduling is intentionally discouraged to protect analytical databases from excessive query pressure.

---

## 2. Dynamic Worker Node Auto-Scaling

### Limitation
Worker concurrency is governed by `DATALENS_WORKER_CONCURRENCY` per instance. Horizontal worker scaling is accomplished via running additional worker replica processes or container replicas.

### Boundary
- There is currently no built-in dynamic autoscaler that spins up additional worker containers based on queue depth metrics. Kubernetes Horizontal Pod Autoscaler (HPA) using custom PostgreSQL queue-depth metrics (`SELECT count(*) FROM background_jobs WHERE status='QUEUED'`) should be configured for hyperscale deployments.

---

## 3. Large Dataset In-Memory Quality Validation

### Limitation
When validating datasets with hundreds of millions of rows, loading entire record sets into Python memory for duplicate checks is constrained by RAM capacity.

### Boundary
- For ultra-large datasets, DataLens leverages DuckDB query pushdowns (`SELECT count(DISTINCT *) FROM read_parquet(...)`) rather than evaluating row dictionaries in Python runtime.

