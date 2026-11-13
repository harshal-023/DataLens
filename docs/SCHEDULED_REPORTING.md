# DataLens — Scheduled Reporting Engine

## Overview

The DataLens Scheduled Reporting Engine enables hands-free, automated report execution based on user-defined frequencies, timezones, and recipient delivery lists.

---

## 1. Schedule Data Model (`report_schedules`)

Each schedule links directly to a `BusinessReport` entity:

| Field | Type | Description |
|---|---|---|
| `id` | String / UUID | Primary identifier (`sched-...`) |
| `report_id` | String / UUID | Foreign key referencing `business_reports.id` |
| `frequency` | Enum / String | `daily`, `weekly`, `monthly`, or `custom` |
| `cron_expression` | String | Standard 5-part cron syntax (e.g., `0 8 * * 1`) |
| `timezone` | String | IANA timezone identifier (e.g., `UTC`, `America/New_York`, `Asia/Kolkata`) |
| `delivery_type` | String | Delivery mode: `email`, `download_ready`, `slack_webhook` |
| `recipients` | JSONB / Array | Validated list of recipient email addresses |
| `is_active` | Boolean | Whether the schedule is actively monitored and triggered |
| `next_run_at` | DateTime (UTC)| Precalculated timestamp for next execution |
| `last_run_at` | DateTime (UTC)| Timestamp of most recent execution |
| `consecutive_failures` | Integer | Consecutive failure counter for error monitoring |

---

## 2. Timezone Resolution & Next Run Calculation

To guarantee schedule execution across heterogeneous environments:
- DataLens computes next execution times using standard Python timezone calculations with fallback to UTC.
- When a schedule executes:
  1. Concurrency locks ensure a single execution instance per schedule.
  2. `ReportRun` is created in status `running`.
  3. The report assembly and document export pipelines run.
  4. Upon completion, `last_run_at` is updated, `consecutive_failures` is reset to 0, and `next_run_at` is advanced to the next occurrence.
  5. In case of failure, `consecutive_failures` is incremented and logged.

---

## 3. Supported Frequencies

- **Daily**: Runs every day at a specified time (e.g., 08:00 AM).
- **Weekly**: Runs on a designated day of the week (e.g., Every Monday at 09:00 AM).
- **Monthly**: Runs on a specified day of the month (e.g., 1st of every month at 06:00 AM).
- **Custom Cron**: Advanced 5-part cron expressions for complex intervals (e.g., bi-weekly or quarter-end).

