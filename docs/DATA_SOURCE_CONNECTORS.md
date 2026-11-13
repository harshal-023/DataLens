# DataLens Data Source Connectors Reference

## 1. Supported Data Sources Overview

DataLens Phase 5A provides enterprise-grade connectivity across six major data source categories:

| Connector | Category | Protocol / Driver | Supported Versions | Security |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | Relational Database | `asyncpg` | 12+ (RDS, Supabase, Neon) | TLS/SSL (`require`), AES-256 |
| **MySQL** | Relational Database | `pymysql` | 5.7, 8.0+, MariaDB 10+ | TLS/SSL, AES-256 |
| **REST API** | Web Services & APIs | `httpx` (async) | HTTP/1.1, HTTP/2 (JSON) | SSRF Filter, Bearer/Key Auth |
| **Google Sheets** | Cloud Spreadsheets | Google Sheets API v4 | Public & Workspace Sheets | OAuth 2.0 with Auto-Refresh |
| **MongoDB** | Document Database | `pymongo` | 4.4, 5.0, 6.0+, Atlas | BSON normalization, URI / Auth |
| **S3 Storage** | Object Storage | `boto3` | AWS S3, MinIO, Wasabi, R2 | SigV4, IAM Key/Secret/Session |

---

## 2. PostgreSQL Connector

- **Configuration Parameters**:
  - `host` (string): Hostname or IP address
  - `port` (integer): Port number (default: `5432`)
  - `database` (string): Target database name
  - `ssl` (boolean or string): Set `true` for mandatory SSL verification
- **Credentials**:
  - `username` (string)
  - `password` (string)
- **Features**:
  - Connection pooling with `asyncpg.create_pool`
  - Automated `information_schema` table & view discovery
  - Unbuffered cursor streaming with transaction isolation
  - Keyset-based watermark filtering for incremental syncs (`WHERE watermark_col > $1 ORDER BY watermark_col ASC`)

---

## 3. MySQL Connector

- **Configuration Parameters**:
  - `host` (string): Hostname or IP address
  - `port` (integer): Port number (default: `3306`)
  - `database` (string): Database schema name
  - `charset` (string): Character set (default: `utf8mb4`)
  - `ssl` (boolean): Enforce SSL connection
- **Credentials**:
  - `username` (string)
  - `password` (string)
- **Features**:
  - Server-side unbuffered cursor via `pymysql.cursors.SSDictCursor`
  - Non-blocking execution wrapped in `asyncio.to_thread`
  - Discovery of all non-system databases and tables
  - Datetime, Decimal, and Binary type sanitization

---

## 4. REST API Connector

- **Configuration Parameters**:
  - `base_url` (string): Target API endpoint root (enforced HTTPS)
  - `auth_type` (string): `none`, `bearer`, `api_key`, `basic`
  - `api_key_header` (string): Header name for API key (e.g. `X-API-Key`)
  - `data_path` (string): Dot-delimited JSON extraction path (e.g. `data.items`)
  - `pagination_type` (string): `none`, `offset_limit`, `page`, `cursor`
  - `page_size` (integer): Number of records requested per page
- **Credentials**:
  - `token` / `api_key` / `username` / `password`
- **Features**:
  - Anti-SSRF DNS resolution guard (blocks private, link-local, loopback networks)
  - Recursive JSON flattener converting nested hierarchies to flat tabular schemas
  - Exponential backoff retry handling for HTTP 429 rate limits and 5xx errors

---

## 5. Google Sheets Connector

- **Configuration Parameters**:
  - `spreadsheet_id` (string): 44-character spreadsheet key from URL
- **Credentials**:
  - `client_id` (string): Google Cloud OAuth 2.0 Client ID
  - `client_secret` (string): Google Cloud OAuth 2.0 Client Secret
  - `refresh_token` (string): Offline OAuth refresh token
  - `access_token` (string): Active temporary access token
- **Features**:
  - Zero-interaction automated access token refresh against `https://oauth2.googleapis.com/token`
  - Multi-tab discovery inspecting all worksheets and grid dimensions
  - Dynamic type inference across column values (Date, Double, Integer, Boolean, String)

---

## 6. MongoDB Connector

- **Configuration Parameters**:
  - `host` (string) & `port` (integer, default: `27017`)
  - `database` (string): Target database name
  - `auth_source` (string): Authentication database (default: `admin`)
- **Credentials**:
  - `uri` (string, optional): Full connection string (e.g. `mongodb+srv://...`)
  - `username` & `password`
- **Features**:
  - Full BSON type normalization converting `ObjectId`, `Decimal128`, `datetime`, and byte arrays into JSON/Parquet types
  - Non-blocking chunked streaming cursor
  - Incremental sync support on `_id` or timestamp fields

---

## 7. S3-Compatible Storage Connector

- **Configuration Parameters**:
  - `bucket` (string): S3 bucket name
  - `region_name` (string): AWS region (e.g. `us-east-1`, `eu-west-1`)
  - `endpoint_url` (string, optional): Custom endpoint for MinIO, Cloudflare R2, or Wasabi
  - `prefix` (string, optional): Key prefix folder filter
- **Credentials**:
  - `access_key_id` & `secret_access_key`
  - `session_token` (optional, for temporary IAM credentials)
- **Features**:
  - Auto-discovery of CSV, TSV, and Parquet files
  - Direct pyarrow-based Parquet row-group extraction
  - Snappy-compressed columnar streaming

