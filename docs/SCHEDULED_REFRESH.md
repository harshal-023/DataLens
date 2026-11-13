# DataLens Scheduled Refresh & Automated Synchronization

## 1. Scheduling Architecture

DataLens provides automated, recurring synchronization pipelines powered by `RefreshSchedulerService` (`backend/app/services/connectors/refresh_scheduler.py`).

Schedules are configured per connection resource and managed through the `DataSourceRefreshConfig` database model.

```
                    ┌───────────────────────────────┐
                    │  Background Job / Cron Runner │
                    └───────────────┬───────────────┘
                                    │ Every minute / periodic tick
                                    ▼
                    ┌───────────────────────────────┐
                    │  RefreshSchedulerService      │
                    │  .trigger_due_refreshes()     │
                    └───────────────┬───────────────┘
                                    │
                                    │ Finds active configs where next_run_at <= NOW
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │  For each due schedule:                                │
        │  1. Check connection status (skip if inactive)         │
        │  2. Compute next execution timestamp                   │
        │  3. Spawn ImportEngine ingestion task                  │
        │  4. Update last_execution_time and last_status         │
        └────────────────────────────────────────────────────────┘
```

---

## 2. Frequency Options & Calculation

| Frequency | Interval | Calculation Method |
| :--- | :--- | :--- |
| **Hourly** | Every 1 hour | `base_time + timedelta(hours=1)` |
| **Daily** | Every 24 hours | `base_time + timedelta(days=1)` (defaults to configured hour/minute) |
| **Weekly** | Every 7 days | `base_time + timedelta(weeks=1)` (on chosen day of week) |
| **Custom Cron**| Custom standard cron | Evaluated via `croniter` parser with timezone offset |

---

## 3. Concurrency Protection & Resilience

To protect remote data sources from resource exhaustion and avoid deadlocks:

1. **Overlap Prevention**: If a previous sync job for the same target resource is currently in `in_progress` status, the scheduler skips triggering a concurrent run and reschedules for the next interval.
2. **Consecutive Failure Backoff**: If an automated sync fails (e.g. database password was changed), `consecutive_failures` is incremented. After 5 consecutive failures, the schedule is automatically paused to prevent server spamming, and an alert is flagged in the dashboard.
3. **Database Transaction Safety**: Each scheduled sync runs within its own transaction boundary; a failure in one connection's sync never impacts others in the batch.

---

## 4. Manual On-Demand Refresh

Users can trigger an immediate manual synchronization at any time:
- Via UI: Click the **Sync** icon on the connection card or detail page.
- Via API:
```http
POST /api/v1/connections/{connection_id}/refresh
Authorization: Bearer <token>
X-Workspace-ID: <workspace_id>
```

The endpoint reuses the active `DataSourceRefreshConfig` or the latest successful import configuration, immediately initiating the ingestion job and returning the new `DataSourceImport` record.

