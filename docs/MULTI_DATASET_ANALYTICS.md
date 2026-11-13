# Multi-Dataset Analytics & Safe Joins

## Cross-Dataset Querying
The Natural Language Analytics engine enables cross-dataset querying by leveraging relationship discovery from Phase 6B (`DatasetRelationship`).

## Relationship Verification & Cardinality Guard
Before constructing cross-dataset queries, DataLens:
1. Verifies that a relationship exists between `source_dataset_id` and `target_dataset_id`.
2. Inspects relationship status (`CONFIRMED` or high-confidence `SUGGESTED`).
3. Evaluates cardinality (`ONE_TO_ONE`, `MANY_TO_ONE`, `ONE_TO_MANY`, `MANY_TO_MANY`).
4. Attaches cardinality warnings when many-to-many joins could produce unintended row inflation.

## Safe DuckDB Compilation
Multi-dataset joins compile into parameterized SQL over separate Parquet file sets:
```sql
SELECT
    CAST(t."segment" AS VARCHAR) AS "segment",
    SUM(s."revenue") AS metric_value,
    COUNT(*) AS record_count
FROM read_parquet(['/data/sales_orders.parquet']) AS s
LEFT JOIN read_parquet(['/data/customers.parquet']) AS t
    ON s."customer_id" = t."customer_id"
GROUP BY t."segment"
ORDER BY metric_value DESC
LIMIT 5
```
By automatically analyzing the physical column schemas of primary and secondary Parquet files, column references are correctly routed to table alias `s` or `t`.

