# DataLens Phase 5D – Timezone-Aware Scheduling Engine

---

## 1. Overview

The DataLens Scheduling Engine calculates recurring and one-time execution timestamps with strict timezone preservation, Daylight Saving Time (DST) transition handling, and missed execution mitigation.

All schedules are evaluated using local time context and persisted in database records normalized to UTC.

---

## 2. Supported Frequencies

| Frequency | Parameters | Example Scenario |
|---|---|---|
| `one_time` | `hour`, `minute`, `timezone` | Run once at a designated future time. |
| `hourly` | `minute`, `timezone` | Sync incremental sales data at :15 past every hour. |
| `daily` | `hour`, `minute`, `timezone` | Run daily batch sync and transformation at 08:30 EST. |
| `weekly` | `day_of_week` (0-6), `hour`, `minute` | Execute Monday morning weekly report at 06:00 UTC. |
| `monthly` | `day_of_month` (1-31), `hour`, `minute` | Monthly executive summary on the 1st of every month. |
| `cron` | `cron_expression` (5 fields) | Complex schedules (e.g. `*/15 * * * 1-5` for business hours). |

---

## 3. Pure-Python 5-Field Cron Parser

Standard cron expressions follow:
$$\text{minute (0-59)} \quad \text{hour (0-23)} \quad \text{day of month (1-31)} \quad \text{month (1-12)} \quad \text{day of week (0-6)}$$

Features:
- Wildcards (`*`)
- Value lists (`1,15,30`)
- Ranges (`1-5`, `9-17`)
- Step intervals (`*/15`, `0-30/5`)
- Zero external dependencies.

---

## 4. Missed Execution Handling & Recovery

When DataLens restarts after scheduled downtime:
1. `BackgroundJobService.trigger_due_schedules` queries all active schedules where `next_run_at <= NOW()`.
2. Automatically queues the single pending execution using a deterministic idempotency key (`sched_<id>_<timestamp>`).
3. Advances `next_run_at` to the subsequent scheduled period to prevent duplicate flood execution.

