# Dataset Joins & Merging Specification

## Join Types Supported

DataLens supports four standard relational joins executed deterministically in DuckDB:

1. **INNER JOIN**: Returns only rows with matching keys in both left and right datasets.
2. **LEFT JOIN**: Returns all rows from the primary (left) dataset and matched rows from the secondary (right) dataset. Missing right-side values are NULL.
3. **RIGHT JOIN**: Returns all rows from the secondary (right) dataset and matched rows from the primary (left) dataset.
4. **FULL OUTER JOIN**: Returns all rows from both datasets. Unmatched values from either side are NULL.

## Join Keys & Multi-Key Matching

- Users can specify one or more key pairs (e.g. `left: customer_id`, `right: id`).
- Key pairs are joined using SQL equality: `left."customer_id" = right."id"`.
- Multiple key pairs are combined using `AND`.

## Collision Resolution & Suffixes

When both datasets contain columns with identical names (e.g. `id`, `created_at`, `status`), DataLens automatically prevents ambiguous column references by appending configurable suffixes:
- Left dataset collision: `"{column}{conflict_suffix_left}"` (default: `_left`, e.g. `id_left`).
- Right dataset collision: `"{column}{conflict_suffix_right}"` (default: `_right`, e.g. `id_right`).
- Non-colliding columns preserve their exact original names.

## Appending & Unions

When combining datasets vertically:
- **UNION ALL**: Appends all rows from secondary datasets.
- **UNION DISTINCT**: Appends rows and eliminates exact duplicate records.
- **Schema Reconciliation**: If secondary datasets lack columns present in the primary table, `NULL AS column_name` is injected automatically so columns remain aligned.

