# Scheduled Business Intelligence Sweeps

## Overview
Phase 6D integrates autonomous insight scanning with the Phase 5D background job orchestration and cron scheduling infrastructure.

## Trigger Types & Sweep Policies
1. **Daily Cadence**: Runs at off-peak hours (e.g., 02:00 AM) to evaluate daily KPI shifts, yesterday's anomalies, and emergent concentration spikes.
2. **Weekly Cadence**: Evaluates week-over-week trends, category trajectory changes, and multi-week sustained momentum signals.
3. **Monthly Cadence**: Comprehensive audit computing MoM, QoQ, and YoY changes, negative margin reviews, and customer HHI concentrations.
4. **On Data Refresh**: Triggered automatically when an external connector or file upload materializes a new `DatasetVersion`.
5. **On Pipeline Completion**: Triggered automatically when an automated transformation workflow successfully completes and publishes an output dataset.

## Schedule Configuration Schema (`insight_generation_schedules`)
- `workspace_id`: The owning workspace.
- `dataset_id`: Optional specific target dataset (or null for all datasets in workspace).
- `schedule_type`: `DAILY`, `WEEKLY`, `MONTHLY`, `ON_REFRESH`, `ON_PIPELINE`.
- `cron_expression`: Standard 5-part cron syntax (e.g., `0 2 * * *`).
- `enabled_categories`: JSON array of active scanners (e.g., `["performance", "trend", "anomaly", "risk", "opportunity"]`).
- `sensitivity_threshold`: Multiplier adjusting anomaly sensitivity (0.5 = loose, 1.0 = standard, 1.5 = strict).
- `min_priority`: Minimum severity threshold to emit notifications (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- `status`: `ACTIVE`, `PAUSED`.

