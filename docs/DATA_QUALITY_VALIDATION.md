# DataLens Phase 5D – Data Quality Validation Gateways

---

## 1. Overview

Before refreshing or materializing derived Parquet datasets into the permanent analytical layer, DataLens executes data quality validation gates to verify integrity, detect schema drift, and prevent silent data corruption.

---

## 2. Validation Checks

1. **Required Columns:**
   - Verifies all critical business dimensions (e.g. `customer_id`, `transaction_date`, `amount`) are present in the output schema.
2. **Column Type Verification:**
   - Ensures data types match expected schema (e.g., numeric fields are integers or floats, not string-serialized values).
3. **Null Percentage Thresholds:**
   - Flags or blocks datasets where null or empty strings exceed the configured maximum percentage (e.g., max 20% null rate).
4. **Duplicate Row Thresholds:**
   - Computes duplicate row percentages across non-metadata fields and alerts if duplicate rates exceed bounds (e.g., max 10%).
5. **Row Count Bounds:**
   - Evaluates minimum row count (`min_row_count`) and maximum row count (`max_row_count`).

---

## 3. Enforcement Actions

| Action | Behavior |
|---|---|
| `BLOCK` | Fails the job with `ErrorClassification.VALIDATION`. The dataset is NOT materialized or updated. |
| `WARN` | Logs a warning in the execution trace and dispatches a notification, but allows materialization to proceed. |
| `REQUIRE_APPROVAL` | Holds the materialized version in draft staging until a workspace admin reviews and approves it. |

