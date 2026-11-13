# Cross-Dataset Relationship Discovery Engine

## 1. Overview
The [`RelationshipDiscoveryEngine`](file:///d:/PE%20CP/backend/app/services/intelligence/relationship_service.py) automatically identifies referential joins and entity relationships between datasets within the same workspace.

---

## 2. Match Detection Criteria

When comparing candidate columns between two datasets in a workspace, the engine scores the pair based on:
1. **Name Matching:**
   - Exact identifier name match (`customer_id` == `customer_id`): +0.50.
   - Normalized name match (`cust_id` vs `customer_id`): +0.40.
   - Foreign key pattern match (`orders.customer_id` -> `customers.id`): +0.55.
2. **Semantic Type Affinity:**
   - Both columns classified with identical semantic types (e.g. both `customer_identifier`): +0.30.
3. **Key Role Compatibility:**
   - Target column is a Primary Key and Source column is a Foreign Key: +0.25.
   - Both columns are Primary Keys (1:1 candidate): +0.20.
4. **Data Type Compatibility:**
   - Matching logical types (`string` vs `string` or `integer` vs `integer`): +0.10.
   - Incompatible types: -0.30 penalty.

Pairs with an overall confidence score `>= 0.60` are registered as suggested relationships.

---

## 3. Cardinality Inference

Cardinality is mathematically determined by evaluating the key properties of the source and target columns:

| Source Unique? | Target Unique? | Inferred Cardinality | Typical Example | Join Warning |
| :--- | :--- | :--- | :--- | :--- |
| **Yes** | **Yes** | `ONE_TO_ONE` | User Details <-> User Profile | None |
| **No** | **Yes** | `MANY_TO_ONE` | Sales Orders (`customer_id`) <-> Customers (`id`) | None |
| **Yes** | **No** | `ONE_TO_MANY` | Dimension <-> Fact table | None |
| **No** | **No** | `MANY_TO_MANY` | Product Tags <-> Order Tags | **Row Multiplication Warning** |

### Many-to-Many Join Warning
When a many-to-many relationship is detected, DataLens automatically attaches an explicit warning:
> *"Many-to-many relationship detected. Joining on these columns may cause row multiplication and distort metric sums."*

---

## 4. Referential Overlap Calculation
Using DuckDB in-memory execution, the engine verifies the actual distinct value overlap across the two datasets:
```sql
WITH s AS (
    SELECT DISTINCT CAST("customer_id" AS VARCHAR) AS val
    FROM read_parquet(['sales.parquet'])
    WHERE "customer_id" IS NOT NULL
),
t AS (
    SELECT DISTINCT CAST("customer_id" AS VARCHAR) AS val
    FROM read_parquet(['customers.parquet'])
    WHERE "customer_id" IS NOT NULL
)
SELECT
    (SELECT COUNT(*) FROM s) AS src_distinct,
    (SELECT COUNT(*) FROM t) AS tgt_distinct,
    (SELECT COUNT(*) FROM s INNER JOIN t ON s.val = t.val) AS common_count;
```
The resulting `overlap_ratio = common_count / src_distinct` proves whether the foreign keys in the source dataset exist in the target dataset.

---

## 5. Confirmation Workflow
- Discovered relationships default to `SUGGESTED`.
- Users can review the match confidence and evidence in the **Relationship Explorer** and click **Confirm** or **Reject**.
- Automatic joins are never executed without user confirmation.

