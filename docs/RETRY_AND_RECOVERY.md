# DataLens Phase 5D – Retry Logic & Failure Recovery

---

## 1. Overview

The Background Job Engine incorporates resilient retry mechanics and automatic state recovery to ensure zero job loss across network blips, temporary service outages, worker crashes, and backend server restarts.

---

## 2. Error Classification

| Error Classification | Retryable? | Behavior |
|---|---|---|
| `TRANSIENT` | **Yes** | Transient network reset, lock contention, timeout. Enqueues retry with exponential backoff. |
| `TIMEOUT` | **Yes** | Step exceeded allocated runtime quota. Retries up to `max_retries`. |
| `AUTHENTICATION` | **No** | Invalid credentials, expired OAuth tokens, 401/403. Fails immediately. |
| `VALIDATION` | **No** | Missing required columns, schema drift, illegal parameters. Fails immediately. |
| `PERMANENT` | **No** | Deleted upstream resource, corrupt binary data. Fails immediately. |

---

## 3. Exponential Backoff Formula

$$\text{delay} = \min\left(\text{retry\_delay\_seconds} \times 2^{\text{attempt} - 1},\; 3600\right)$$

*Example with base delay 30 seconds:*
- Attempt 1: 30 seconds
- Attempt 2: 60 seconds
- Attempt 3: 120 seconds

---

## 4. Stale Job & Crash Recovery

When a worker crashes or a backend process is killed:
1. `heartbeat_at` stops updating.
2. `BackgroundJobService.recover_stale_jobs` runs periodically or on worker startup.
3. Any job in `RUNNING` state where $\text{NOW}() - \text{heartbeat\_at} > \text{threshold}$ (default 10 min) is flagged as stalled.
4. Stalled jobs transition to `FAILED` with `ErrorClassification.TIMEOUT` and retry if attempts remain.

