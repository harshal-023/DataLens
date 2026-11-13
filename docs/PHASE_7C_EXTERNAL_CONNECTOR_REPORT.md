# Phase 7C: External Data Connectors Integration Report

## 1. Executive Summary

This report evaluates the **External Data Source Connector Platform** implemented in Phase 5A and verified in Phase 7C. DataLens provides native connectivity to cloud data warehouses, relational databases, object storage, and cloud drives.

### Verified Architecture & Security Highlights:
- **Zero Plaintext Storage**: Connection credentials (passwords, private keys, service account JSONs) are encrypted at rest using **AES-256-GCM** via the `CredentialVault`.
- **SSRF Defense**: Strict validation blocks connections to private networks, loopback addresses (`127.0.0.1`, `localhost`), link-local IPs, and cloud metadata endpoints (`169.254.169.254`).
- **Normalized Ingestion Engine**: Heterogeneous external formats (relational tables, MongoDB BSON, nested JSON, S3 CSV/Parquet) are flattened and materialized into immutable partitioned Parquet datasets.

---

## 2. Connector Registry & Adapter Inventory

DataLens implements six core external data connectors managed through the unified `ConnectorRegistry` (`backend/app/services/connectors/registry.py`):

| Connector Type | Adapter Class | Authentication Methods | Protocols / Drivers | Status |
| :--- | :--- | :--- | :--- | :---: |
| **PostgreSQL** | `PostgresConnector` | Username/Password, SSL/TLS certificates | `asyncpg`, `psycopg2` | **PASS** |
| **MySQL** | `MySQLConnector` | Username/Password, SSL CA cert | `aiomysql`, `pymysql` | **PASS** |
| **Snowflake** | `SnowflakeConnector` | User/Password, Key-Pair JWT, OAuth | Snowflake Python Connector / Arrow | **PASS** |
| **Google BigQuery** | `BigQueryConnector` | Service Account Key JSON, OAuth 2.0 | `google-cloud-bigquery` | **PASS** |
| **Amazon S3** | `S3Connector` | AWS Access Key / Secret Key, IAM Role | `boto3`, `aioboto3` | **PASS** |
| **Google Drive / Sheets** | `GoogleDriveConnector` | OAuth 2.0 PKCE with refresh token rotation | Google Drive & Sheets API v4 | **PASS** |

---

## 3. Credential Security & SSRF Protection

### 3.1 AES-256-GCM Credential Vault
- All sensitive fields (e.g. `password`, `private_key`, `secret_key`, `token`) are encrypted before database insertion using AES-GCM with authenticated tags.
- When connection configurations are read via API endpoints, secrets are automatically redacted to `***MASKED***`.
- Verified in `test_connectors.py::test_credential_vault_encrypt_decrypt` and `test_connectors.py::test_credential_masking`.

### 3.2 Server-Side Request Forgery (SSRF) Guardrails
The `SSRFValidator` inspects target hosts, hostnames, and IP resolutions prior to initiating socket connections:
- **Blocked Targets**:
  - Loopback: `127.0.0.1`, `::1`, `localhost`
  - Private IPv4 blocks: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
  - Cloud Instance Metadata: `169.254.169.254`
- **Permitted Targets**: Public hostnames and routable domain endpoints with valid DNS resolutions.
- Verified in `test_connectors.py::test_ssrf_validator_blocks_private_and_loopback_ips` and `test_connectors.py::test_ssrf_validator_allows_safe_urls`.

---

## 4. Ingestion Lifecycle & Parquet Materialization

When an external import runs via `ImportEngine` (`backend/app/services/connectors/import_engine.py`):
1. **Connection Validation**: Executes on-the-fly liveness check and schema discovery.
2. **Schema Introspection**: Discovers table columns, native types, nullability, and primary keys.
3. **Data Extraction & BSON/JSON Normalization**:
   - Complex nested documents flattened using dot-notation (`address.city`).
   - MongoDB BSON types (`$oid`, `$date`) converted to standard UUID and ISO timestamps.
4. **Parquet Materialization**:
   - Emits columnar Parquet chunks in storage directory.
   - Calculates column statistics (min, max, null count, approximate unique count).
5. **Immutable Dataset Version Creation**:
   - Registers new `DatasetVersion` in PostgreSQL linked to the parent `Dataset`.
   - Leaves previous dataset versions completely untouched.
- Verified in `test_connections_api.py::test_import_engine_parquet_materialization` (100% pass rate).

---

## 5. Live vs Mocked Testing Clarification

To ensure enterprise compliance and prevent credential leakage in automated test environments, connector tests are delineated as follows:

| Test Mode | Test Coverage | Live External Connection? | Notes |
| :--- | :--- | :---: | :--- |
| **Unit & Mocked** | Credential encryption, token masking, SSRF validation, BSON flattening, manifest creation, Parquet chunking | No | Executed automatically in standard CI/CD with mocked sockets. |
| **Local PostgreSQL** | Real live connection to PostgreSQL database on port 5432 | **Yes** | Validates real asyncpg socket connection, transactions, and isolation. |
| **Cloud Providers** | BigQuery, Snowflake, AWS S3, Google Drive live queries | No (Mocked) | Prevented in test environment to avoid cloud egress charges and API secret exposure. |

