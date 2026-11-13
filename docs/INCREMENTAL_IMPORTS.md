# Incremental Ingestion & High-Watermark Architecture

## 1. Concept and Overview

Full snapshots are suitable for smaller lookup tables or static files, but synchronizing large production tables (e.g. 10M+ transaction records) requires **Incremental Ingestion**.

DataLens implements a high-watermark synchronization engine that extracts only new or updated records since the previous successful sync, generating a new immutable dataset version without overwriting the previous version.

---

## 2. High-Watermark Mechanism

```
Previous Sync:
  Watermark Column: `updated_at`
  Stored Watermark: `2026-11-12T00:00:00Z`
  Dataset Version:  `v1.0` (100,000 rows)

New Sync:
  Query Filter:     `WHERE updated_at > '2026-11-12T00:00:00Z'`
  Extracted Rows:   `1,420 rows`
  New Max Value:    `2026-11-12T12:00:00Z`
  Dataset Version:  `v2.0` (Materialized with updated records)
```

---

## 3. Watermark Column Selection Guidelines

For incremental syncs to operate correctly, the watermark column must satisfy two properties:
1. **Monotonically Increasing**: Newly inserted or updated records must have a value strictly greater than previously synced records.
2. **Indexed in Source**: The remote database should have an index (B-tree or compound) on the watermark column for optimal extraction performance.

### Recommended Watermark Column Types
- `updated_at`, `modified_at`, `last_modified` (Timestamp with timezone)
- `created_at` (Append-only logs or event streams)
- `id`, `sequence_id` (Autoincrement / serial primary key)
- `_id` (MongoDB ObjectId, which embeds a 4-byte timestamp)

---

## 4. Driver Query Construction

The connector applies watermark filtering natively:

### PostgreSQL
```sql
SELECT * FROM "public"."orders"
WHERE "updated_at" > $1
ORDER BY "updated_at" ASC;
```

### MySQL
```sql
SELECT * FROM `production`.`orders`
WHERE `updated_at` > %s
ORDER BY `updated_at` ASC;
```

### MongoDB
```json
{
  "$gt": ISODate("2026-11-12T00:00:00Z")
}
```
Or for `_id`:
```json
{
  "_id": { "$gt": ObjectId("6732f7a0...") }
}
```

### REST API
Parameterized query string:
`https://api.example.com/v1/orders?updated_at_gt=2026-11-12T00:00:00Z`

---

## 5. Version Immutability & Provenance

When an incremental import completes:
1. The original version (`v1.0`) remains completely untouched on disk.
2. The new version (`v2.0`) is registered with the new row count and checksum.
3. Dashboards and reports pinned to `v1.0` continue to display historical data.
4. Dashboards set to track `current_version` immediately reflect the latest synchronized data.

