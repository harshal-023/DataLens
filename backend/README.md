# DataLens Backend — Phase 2A Foundation & API Architecture

This directory contains the Python FastAPI backend for **DataLens**, providing an asynchronous API architecture powered by PostgreSQL, SQLAlchemy 2.x, Alembic, and Pydantic v2.

---

## 1. Architecture Overview

- **Framework:** FastAPI with Uvicorn (ASGI)
- **Database Engine:** SQLAlchemy 2.x (Asynchronous via `asyncpg`)
- **Schema & Migrations:** Alembic with async migration runner
- **Configuration & Validation:** Pydantic v2 & `pydantic-settings`
- **Security:** Argon2id password hashing (`argon2-cffi`), strict CORS allowlist
- **Storage Abstraction:** Pluggable `StorageBackend` interface with `LocalStorageBackend` implementation (UUID keys, path traversal protection)
- **API Versioning:** Versioned under `/api/v1`

---

## 2. Directory Layout

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py          # Liveness & readiness probes
│   │       └── router.py              # Central v1 router
│   ├── core/
│   │   ├── config.py                  # Typed settings from .env
│   │   ├── exceptions.py              # Domain exceptions & error handlers
│   │   ├── logging.py                 # Structured application logging
│   │   └── security.py                # Argon2id password hashing
│   ├── db/
│   │   ├── base.py                    # Base DeclarativeBase & UUID/Timestamp mixins
│   │   └── session.py                 # Async engine & session dependency injection
│   ├── dependencies/                  # Injected request dependencies
│   ├── models/                        # SQLAlchemy relational models
│   │   ├── user.py
│   │   ├── workspace.py
│   │   ├── dataset.py
│   │   ├── dataset_version.py
│   │   ├── analysis_run.py
│   │   └── report.py
│   ├── repositories/                  # Data access layer
│   ├── schemas/                       # Pydantic request/response schemas
│   │   ├── common.py
│   │   └── health.py
│   ├── services/                      # Domain services
│   ├── storage/                       # Storage backend abstraction
│   │   ├── base.py
│   │   └── local.py
│   └── main.py                        # FastAPI application entry point
├── alembic/
│   ├── env.py                         # Async Alembic configuration
│   └── versions/
│       └── 20261111_0001_initial_schema.py
├── tests/                             # Automated test suite
├── alembic.ini
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 3. Getting Started

### Prerequisites

- Python 3.12+ (Python 3.13 supported)
- PostgreSQL 15+ (or Docker)

### Installation

1. Create and activate a Python virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

---

## 4. PostgreSQL Database Setup

### Option A: Using Docker Compose
From the project root:
```bash
docker compose up -d postgres
```

### Option B: Using Local PostgreSQL
Create a database named `datalens`:
```sql
CREATE DATABASE datalens;
```

Update your `.env` connection string:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/datalens
```

---

## 5. Database Migrations (Alembic)

To apply migrations to your PostgreSQL database:
```bash
cd backend
alembic upgrade head
```

To view SQL without executing:
```bash
alembic upgrade head --sql
```

To roll back the last migration:
```bash
alembic downgrade -1
```

---

## 6. Running the API Server

Start the development server with live reload:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints:
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Probe:** `GET /api/v1/health`
- **Readiness Probe:** `GET /api/v1/health/ready`

---

## 7. Testing & Code Quality

Run tests:
```bash
cd backend
pytest -v
```

Run Ruff linter:
```bash
cd backend
ruff check .
```

