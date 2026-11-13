# DataLens Phase 5A: Known Limitations & Operational Boundaries

## Overview

This document describes technical constraints, rate-limit boundaries, and edge-case behaviors identified during the Phase 5A implementation of the Enterprise External Data Source Integration Platform.

---

## 1. Third-Party Rate Limits & Quotas

### Google Sheets API v4
- **Per-User Quota**: Google enforces a limit of 60 read requests per user per minute and 300 per project per minute.
- **Operational Boundary**: Synchronizing spreadsheets with more than 100 individual tabs in rapid succession may trigger HTTP 429 rate limits.
- **Mitigation**: DataLens implements exponential backoff retry logic with jitter. For multi-million row datasets, users should migrate data into PostgreSQL or S3 instead of Google Sheets.

### REST API Endpoints
- External third-party APIs (e.g. Stripe, Salesforce, Shopify) enforce custom rate limits.
- **Mitigation**: Users can configure the `rate_limit_delay` parameter in REST API connection settings (default: 50ms delay between paginated requests).

---

## 2. Dynamic Schema Drift in NoSQL & JSON Data

### MongoDB & REST API Polymorphism
- In MongoDB and unstructured REST APIs, different documents within the same collection or endpoint may have divergent keys or contradictory data types (e.g., `user_id` stored as an integer in older documents and as a string/UUID in newer documents).
- **Behavior**: The `ImportEngine` resolves type conflicts by coercing mixed types to UTF-8 strings.
- **Operational Recommendation**: Users should define schema validation rules in MongoDB or use Phase 4B Data Transformations to clean and cast types after ingestion.

---

## 3. Watermark Incremental Sync Edge Cases

1. **Non-Monotonic Updates**: If a remote table update fails to update the designated watermark column (e.g. an application executes `UPDATE orders SET status = 'shipped'` without touching `updated_at`), the incremental sync will not capture the update.
2. **Clock Skew**: If the database server clock is skewed or transactions commit out of order within the same millisecond, a watermark query using strict inequality (`>`) could theoretically omit records committed in the same microsecond.
3. **Mitigation**: Schedule periodic full snapshot imports (e.g., weekly full sync + hourly incremental sync).

---

## 4. Object Storage File Size Limits

- **CSV Files**: Ingesting unindexed CSV files larger than 5 GB from S3 is bounded by download network bandwidth.
- **Parquet Files**: For datasets larger than 10 GB, native Parquet format is strongly recommended. Parquet utilizes columnar compression, dictionary encoding, and PyArrow row-group streaming, which reduces network I/O by up to 85%.

---

## 5. Network Egress and Firewall Requirements

- For self-hosted PostgreSQL and MySQL databases behind private corporate firewalls, database administrators must whitelist the DataLens server egress IP and ensure database user credentials have `SELECT` privileges on the target schemas and `information_schema`.

