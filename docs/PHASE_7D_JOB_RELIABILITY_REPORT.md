# DATALENS – PHASE 7D: BACKGROUND JOB RELIABILITY & ORCHESTRATION REPORT

## 1. Executive Summary

This report evaluates the reliability, fault tolerance, concurrency safety, and state durability of the DataLens background job orchestration platform (`BackgroundJobService` and `JobWorker`).

**Overall Job Reliability Status:** `PASS`

---

## 2. PostgreSQL-Backed Durability (Zero Redis Dependency)

### 2.1 State Persistence Architecture
DataLens persists all background job states directly in PostgreSQL:
- **Primary Model:** `BackgroundJob` (table `background_jobs`).
- **Execution History:** `JobExecution` (table `job_executions`), recording historical attempts, run durations, error traces, and worker IDs.
- **Schedules:** `JobSchedule` (table `job_schedules`), storing cron expressions, active flags, and `next_run_at` timestamps.

### 2.2 Survivability Under Worker Crashes & Restarts
Because job queues and execution checkpoints are committed to PostgreSQL transactions:
- Zero job state is lost during unexpected worker crashes, container restarts, or backend server reboots.
- Unclaimed jobs remain in status `QUEUED` until picked up.
- Stalled jobs are automatically identified and recovered by the stale job detection worker.

---

## 3. Atomic Job Claiming & Concurrency Controls

### 3.1 `SELECT ... FOR UPDATE SKIP LOCKED`
To enable concurrent multi-worker job consumers without race conditions, `BackgroundJobService.claim_next_job` executes:

```sql
SELECT * FROM background_jobs
WHERE status = 'QUEUED' AND scheduled_at <= NOW()
ORDER BY priority DESC, scheduled_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

### 3.2 Dual Worker Invariant
- `SKIP LOCKED` guarantees that no two workers can claim or execute the same job concurrently.
- If Worker A claims Job 1, Worker B's query skips Job 1 without blocking and immediately acquires Job 2.
- Verified in `backend/tests/test_automation_orchestration.py` with multi-worker concurrent claiming simulations.

---

## 4. Stale Job Recovery & Worker Heartbeats

### 4.1 Heartbeat Protocol
- Active workers send periodic heartbeats (`BackgroundJobService.send_heartbeat`) updating `heartbeat_at` on the active `BackgroundJob`.
- Heartbeats include `progress_pct` (0-100%) and a progress message string for UI dashboard transparency.

### 4.2 Stale Job Recovery (`recover_stale_jobs`)
- A periodic daemon inspects jobs in status `RUNNING` whose last heartbeat timestamp is older than the configured threshold (default: 600 seconds / 10 minutes):
  ```sql
  SELECT * FROM background_jobs
  WHERE status = 'RUNNING'
    AND (heartbeat_at IS NULL OR heartbeat_at < NOW() - INTERVAL '600 seconds');
  ```
- Stale jobs are automatically failed with error classification `TIMEOUT` ("Worker crashed or heartbeat timed out").
- If the job's retry count is below `max_retries`, it is re-enqueued for another attempt with exponential backoff.

---

## 5. Retry Mechanism & Idempotency

### 5.1 Retry Schedule & Backoff
- Retry interval formula:
  $$\Delta t = \text{retry\_delay\_seconds} \times (2^{\text{retry\_count}})$$
- Jobs exceeding `max_retries` transition permanently to `FAILED` status, and failure alert notifications are dispatched to workspace owners.

### 5.2 Idempotency Key De-duplication
- Jobs support an optional `idempotency_key` constraint.
- Duplicate enqueue requests with the same idempotency key return the existing active job rather than enqueuing duplicate executions.

---

## 6. Verification Summary

| Capability | Architecture Implementation | Status |
|:---|:---|:---:|
| Queue Durability | PostgreSQL relational schema (`background_jobs`) | `PASS` |
| Atomic Claiming | PostgreSQL `FOR UPDATE SKIP LOCKED` | `PASS` |
| Concurrent Worker Safety | Zero double-execution across workers | `PASS` |
| Stale Job Recovery | Automatic timeout detection on heartbeat lapse | `PASS` |
| Exponential Retry | Backoff calculation with max retry limits | `PASS` |
| Execution History | Append-only execution auditing (`job_executions`) | `PASS` |

