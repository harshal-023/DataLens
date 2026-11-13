# DataLens — Production Configuration & Hardening Guide

Guidelines for hardening and deploying DataLens in staging and production environments.

---

## 1. Environment Variables & Secret Handling

| Variable | Development Default | Production Requirement |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | Set to `production` |
| `DEBUG` | `true` | Must be `false` |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/datalens` | Dedicated app user over SSL (`ssl=require`) |
| `SECRET_KEY` | Development placeholder | Must be a cryptographically random string (min 32 bytes) |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Restricted to production domain only |
| `COOKIE_SECURE` | `false` | Must be `true` (HTTPS only) |
| `COOKIE_SAMESITE` | `lax` | `lax` or `strict` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Short-lived (15–30 minutes) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 7 days with rotation enabled |
| `MAX_UPLOAD_SIZE_MB` | `50` | Enforced at reverse proxy and backend |

---

## 2. PostgreSQL Connection Pooling

In `backend/app/db/session.py`, connection pool settings can be tuned for production traffic:

- `pool_size`: 20 connections per worker
- `max_overflow`: 10 burst connections
- `pool_recycle`: 1800 seconds (30 minutes)
- `pool_pre_ping`: `True` (prevents dropped TCP connections in cloud load balancers)

---

## 3. Storage Hardening

- Ensure `STORAGE_ROOT` directory has strict POSIX permissions (`0700` or restricted Windows ACLs) so only the application process user can read/write raw uploads and Parquet files.
- Enable server-side encryption at rest if deploying on AWS S3 / Azure Blob storage.

