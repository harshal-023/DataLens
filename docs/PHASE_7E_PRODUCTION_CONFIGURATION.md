# DataLens Phase 7E: Production Configuration Audit & Standards

## 1. Executive Summary

This document specifies the audited production configuration baseline for the DataLens platform. It defines mandatory environment variables, secret management standards, database connection pool tuning, CORS/HTTPS/Cookie security policies, AI privacy guardrails, file storage limits, background worker controls, and single-scheduler enforcement.

---

## 2. Environment Variables Specification

All sensitive configuration must be supplied via environment variables or a cloud secret manager (e.g., AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager). Secrets must **never** be hardcoded or checked into source control.

| Variable Name | Required | Default / Example Value | Description & Security Policy |
| :--- | :---: | :--- | :--- |
| `APP_NAME` | Yes | `DataLens BI Platform` | Human-readable application name displayed in headers and logs. |
| `APP_ENV` | Yes | `production` | Environment mode (`production`, `staging`, `development`). When `production`, swagger docs and debug traces are disabled. |
| `DEBUG` | Yes | `false` | Must be strictly `false` in production. Controls OpenAPI docs and stack trace exposure. |
| `API_V1_PREFIX` | Yes | `/api/v1` | URL prefix for REST API endpoints. |
| `SECRET_KEY` | Yes | *[Cryptographically Secure 64-char string]* | Master secret used for signing JWT access tokens and hashing credentials. Minimum 256 bits. |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/db` | PostgreSQL connection string using the `asyncpg` async driver. Must enforce TLS in production. |
| `DB_POOL_SIZE` | Yes | `20` | Base number of concurrent database connections maintained in the pool per worker. |
| `DB_MAX_OVERFLOW` | Yes | `40` | Maximum transient connections allowed above `DB_POOL_SIZE` during traffic bursts. |
| `DB_POOL_RECYCLE` | Yes | `1800` | Connection recycling timeout in seconds (30 mins) to prevent stale socket accumulation. |
| `DB_POOL_PRE_PING` | Yes | `true` | Validates connection vitality before issuing queries (`SELECT 1`). |
| `CORS_ORIGINS` | Yes | `https://datalens.yourcompany.com` | Strict comma-separated list of allowed origins. Wildcards (`*`) are prohibited. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | `60` | JWT access token lifespan (1 hour). Paired with rotating refresh tokens. |
| `STORAGE_ROOT` | Yes | `/var/lib/datalens/storage` | Root path for Parquet dataset partitions, manifests, and report artifacts. |
| `MAX_UPLOAD_SIZE_MB` | Yes | `100` | Maximum multipart upload file size in megabytes. Enforced before stream buffering. |
| `AI_PROVIDER` | Yes | `gemini` | Primary AI provider (`gemini`, `ollama`, `hybrid`). |
| `GEMINI_API_KEY` | Optional | *[Encrypted Key]* | Google Gemini API key. Required only if `AI_PROVIDER=gemini` or `hybrid`. |
| `GEMINI_MODEL` | Yes | `gemini-3.5-flash` | Gemini model name for natural language analytics and narrative generation. |
| `AI_ENABLED` | Yes | `true` | Master feature flag for AI capabilities. |
| `AI_SEND_SAMPLE_VALUES` | Yes | `false` | **Critical Privacy Rule**: Must be `false` in production to prevent sending row samples to external LLMs. |

---

## 3. Database & Connection Pool Configuration

### 3.1 SQLAlchemy & AsyncPG Engine
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,          # 20
    max_overflow=settings.DB_MAX_OVERFLOW,    # 40
    pool_recycle=settings.DB_POOL_RECYCLE,    # 1800s (30m)
    pool_pre_ping=settings.DB_POOL_PRE_PING,  # True
    poolclass=QueuePool,
    connect_args={
        "server_settings": {
            "application_name": "datalens_backend",
            "statement_timeout": "30000",       # 30 second statement timeout
            "idle_in_transaction_session_timeout": "10000", # 10s idle in tx timeout
        }
    }
)
```

### 3.2 Connection Isolation & SSL
In production deployments:
- Set `ssl=require` or `ssl=verify-full` on `DATABASE_URL`.
- Enforce least-privilege PostgreSQL user accounts (the application user should have `SELECT, INSERT, UPDATE, DELETE` on public schema tables, but not `SUPERUSER`).

---

## 4. Web Security, CORS & Cookie Architecture

### 4.1 CORS Policy
CORS middleware is registered in `backend/app/main.py`:
- `allow_origins`: Strictly resolved from `settings.CORS_ORIGINS`.
- `allow_credentials`: `True` to allow cross-origin cookie sharing only between trusted domains.
- `allow_methods`: Restricted to `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]`.
- `allow_headers`: Explicit list including `Authorization`, `Content-Type`, `X-Workspace-ID`, `X-CSRF-Token`.

### 4.2 Secure Cookie Delivery
Refresh tokens and session indicators are delivered via HTTP cookies with strict attributes:
- `HttpOnly`: `True` (prevents JavaScript access and mitigates XSS token exfiltration).
- `SameSite`: `Lax` (prevents CSRF while allowing standard top-level navigation).
- `Secure`: `True` (enforced when `APP_ENV=production`, preventing plain HTTP transmission).
- `Path`: Restricted to `/api/v1/auth`.

### 4.3 Error Handling & Information Disclosure
- `DEBUG=false` suppresses FastAPI automatic interactive OpenAPI and ReDoc documentation (`docs_url=None`, `redoc_url=None`, `openapi_url=None`).
- Global exception handlers catch unhandled `Exception` instances and return structured JSON responses with an internal tracking `code`, concealing all Python stack traces and database internal details from external clients.

---

## 5. AI Privacy & Guardrails Architecture

The DataLens Unified AI Architecture enforces strict zero-data-leakage policies:

1. **Schema & Semantic Only**:
   - Only column metadata, types, aggregated metrics, and statistical summaries are provided in AI prompts.
   - Raw dataset rows and individual record values are **never** transmitted to Google Gemini.
2. **Explicit Fallback Mode**:
   - If the external AI provider is unreachable or rate-limited, the system falls back seamlessly to the deterministic local analytical rule engine, ensuring business continuity.
3. **Safe Query Compilation**:
   - The AI planner only produces structured analytical JSON plans (`AnalyticalQueryPlan`).
   - The platform compiles SQL deterministically in `backend/app/services/nla/compiler.py` and executes only `SELECT` operations within isolated in-memory DuckDB instances.
   - Arbitrary SQL, DDL, DML, or code generation from LLMs is strictly forbidden.

---

## 6. Background Job Engine & Single-Scheduler Enforcement

DataLens relies on a PostgreSQL-backed job orchestration system (`background_jobs` table).

### 6.1 Avoiding Duplicate Scheduler Runs
When horizontal auto-scaling scales FastAPI API workers (e.g., 4 or 8 Uvicorn processes), a background scheduler must **not** run inside each API worker, which would duplicate scheduled jobs.

**Production Pattern**:
- Run API workers with scheduler initialization disabled (`ENABLE_EMBEDDED_SCHEDULER=false`).
- Run exactly **one dedicated scheduler container/pod** (`python -m app.services.automation.scheduler_runner`).
- Workers claim tasks using PostgreSQL atomic row locking:
  ```sql
  SELECT * FROM background_jobs 
  WHERE status = 'QUEUED' AND scheduled_at <= NOW()
  ORDER BY priority DESC, created_at ASC
  LIMIT 1 FOR UPDATE SKIP LOCKED;
  ```
- This guarantees that even with multiple worker processes running, **every job is claimed and executed exactly once**.

---

## 7. Audit Logging & Secret Masking

1. **Credential Vault**:
   - All credentials for external data sources (PostgreSQL, MySQL, S3, MongoDB) are encrypted using AES-256 via `backend/app/connectors/security.py` before insertion into PostgreSQL.
   - All API endpoints returning connection metadata automatically invoke `mask_credentials()`, redacting passwords, tokens, and private keys.
2. **Tamper-Evident Audit Chain**:
   - All administrative actions, data exports, permissions changes, and shares are logged in `enterprise_audit_logs`.
   - Each log entry calculates a cryptographic SHA-256 hash chaining back to the `previous_hash`, guaranteeing audit log immutability and verifiable tamper-evidence.

