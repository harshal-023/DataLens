# DataLens — Phase 5A Architecture Plan
## Enterprise External Data Source Integration Platform

### 1. Architectural Vision

Phase 5A extends DataLens from a file-upload BI system into an enterprise data platform that connects directly to external databases, APIs, cloud spreadsheets, document stores, and object storage.

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           EXTERNAL SOURCES                             │
  │   [PostgreSQL]  [MySQL]  [REST API]  [Google Sheets]  [MongoDB]  [S3]  │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                      UNIFIED CONNECTOR ENGINE                          │
  │    BaseConnector: test_connection | discover | preview | stream_data   │
  │    Security: AES-256-GCM Credential Vault | SSRF Protection Guard      │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                     UNIFIED DATA IMPORT ENGINE                         │
  │  - Chunked Streaming / Cursor Pagination                               │
  │  - Schema & Type Normalization (PyArrow Table Batches)                 │
  │  - Partitioned Immutable Parquet Storage                               │
  │  - Provenance Tracking (Connection ID, Resource, Watermark, SHA-256)   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                         DATALENS CORE PLATFORM                         │
  │  DatasetService ──► Immutable DatasetVersion ──► Data Studio / Profiler│
  │                                ├──► Transformation Engine              │
  │                                ├──► Interactive Dashboards             │
  │                                ├──► AI Analytics & Prompt Lab          │
  │                                └──► Automated Business Reports         │
  └────────────────────────────────────────────────────────────────────────┘
```

---

### 2. Six Connector Specifications

1. **PostgreSQL Connector (`PostgresConnector`)**:
   - Connection via `asyncpg` with SSL modes (`disable`, `prefer`, `require`).
   - Discovery of databases, schemas, and tables via `information_schema`.
   - Streaming via server-side cursors in chunks of 5,000–50,000 rows.
   - Incremental imports via watermark column (`WHERE col > :last_watermark ORDER BY col ASC`).

2. **MySQL Connector (`MySQLConnector`)**:
   - Connection via `pymysql` with SSL configuration.
   - Discovery of schemas, tables, views, and data types via `information_schema`.
   - Server-side cursor streaming to minimize RAM pressure.
   - Watermark-based incremental refresh.

3. **REST API Connector (`RestApiConnector`)**:
   - Asynchronous HTTP client via `httpx`.
   - Authentication: None, API Key (Header/Query), Bearer Token, Basic Auth, Custom Headers.
   - Security: SSRF validation denying private, link-local, loopback IPs, and enforcing HTTPS by default.
   - Automatic nested JSON flattening into relational tabular schemas.
   - Pagination strategies: Offset/Limit, Page number, Cursor, Link headers.

4. **Google Sheets Connector (`GoogleSheetsConnector`)**:
   - Google OAuth 2.0 authorization code flow with secure token refresh.
   - Discovery of user spreadsheets and worksheets.
   - Grid data preview and type inference.
   - Parquet streaming ingestion.

5. **MongoDB Connector (`MongoConnector`)**:
   - MongoDB connection strings (`mongodb://` and `mongodb+srv://`).
   - Database and collection discovery.
   - Document flattening and BSON type normalization (ObjectId, ISODate, Decimal128).
   - Chunked batch cursor iteration.
   - Incremental change tracking via `_id` or timestamp fields.

6. **S3-Compatible Object Storage Connector (`S3Connector`)**:
   - `boto3` client with configurable endpoint (AWS S3, MinIO, Cloudflare R2, Ceph).
   - Authentication via Access Key, Secret Key, and optional Session Token.
   - Bucket and file discovery (.csv, .tsv, .parquet, .json).
   - Byte-range / streaming download and conversion to DataLens immutable Parquet.

---

### 3. Credential Vault & Encryption
- AES-256-GCM authenticated symmetric encryption with 12-byte random IV/nonce per record.
- Derived from application `SECRET_KEY`.
- No plaintext credentials stored in database or exposed in frontend state or API logs.
- Sensitive fields masked (`••••••••`) across all UI and API read endpoints.

---

### 4. Database Entities
- `data_source_connections`: Workspace-scoped connection configurations and encrypted secrets.
- `data_source_imports`: Import job execution history, progress, row counts, and dataset version references.
- `data_source_table_metadata`: Cached schema discovery for fast browsing.
- `data_source_refresh_configs`: Automated recurring refresh schedules and watermark states.

