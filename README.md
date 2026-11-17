# DataLens 1.0 — Enterprise AI-Powered Business Intelligence Platform

[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-blue.svg)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-18.3-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1-FFF000.svg)](https://duckdb.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg)](https://www.postgresql.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg)](https://tailwindcss.com/)

DataLens is a modern, enterprise-grade Business Intelligence platform designed for non-technical business leaders and data teams alike. It combines deterministic query engines (DuckDB), semantic dataset intelligence, conversational AI analytics (Google Gemini & Ollama), and intuitive visual dashboard builders inspired by Power BI.

---

## Table of Contents

- [1. Introduction](#1-introduction)
- [2. Main Features](#2-main-features)
- [3. The Five Primary Modules](#3-the-five-primary-modules)
- [4. Technology Stack](#4-technology-stack)
- [5. System Architecture Overview](#5-system-architecture-overview)
- [6. Project Folder Structure](#6-project-folder-structure)
- [7. Prerequisites](#7-prerequisites)
- [8. Backend Installation & Startup](#8-backend-installation--startup)
- [9. Frontend Installation & Startup](#9-frontend-installation--startup)
- [10. PostgreSQL Database Setup](#10-postgresql-database-setup)
- [11. Environment Variable Configuration](#11-environment-variable-configuration)
- [12. Database Migrations (Alembic)](#12-database-migrations-alembic)
- [13. Running Automated Tests](#13-running-automated-tests)
- [14. Production Build Instructions](#14-production-build-instructions)
- [15. Deployment Overview](#15-deployment-overview)
- [16. Security & Governance Notes](#16-security--governance-notes)

---

## 1. Introduction

DataLens eliminates the traditional friction of business analytics. Users can upload raw CSV or Excel spreadsheets, immediately receive automated data profiling, query datasets in natural language, run machine learning forecasts, and generate complete interactive dashboards with one click—all backed by zero-trust security and immutable data versioning.

---

## 2. Main Features

- **Autonomous AI Dashboard Generator**: One-click generation of verified KPIs, time-series charts, breakdowns, and business insights from raw datasets.
- **Conversational AI Data Analyst**: Ask natural language questions with deterministic DuckDB query verification, guardrails, and conversational intent routing.
- **Visual Drag-and-Drop Dashboard Builder**: Power BI-inspired canvas with real-time cross-filtering, color themes, threshold alerts, and instant drill-downs.
- **Immutable Dataset Versioning & Ingestion**: Ingest CSV/Excel into partitioned, high-performance Apache Parquet storage with automated schema inference.
- **Enterprise Reports Library & Automated Refresh**: Pixel-perfect PDF/Excel exports, executive report builder, and scheduled background sweeps.
- **Multi-Tenant Workspaces & RBAC**: Role-based access control (Owner, Admin, Editor, Viewer), invite flows, activity audit logs, and CSRF protection.

---

## 3. The Five Primary Modules

| Module | Route | Capabilities |
| :--- | :--- | :--- |
| **Data Management** | `/data` | Dataset upload, preview, version history, schema management, external database connections (PostgreSQL). |
| **Analytics & Dashboards** | `/dashboards` | Interactive dashboard canvas, AI Auto Dashboard generator, widget customization, visual themes, cross-filtering. |
| **AI Data Analyst** | `/ask` | Conversational analytics, DuckDB query execution, chart recommendations, intent routing, audit trails. |
| **Reports** | `/reports` | Multi-page executive reports, PDF/DOCX/Excel export engines, scheduled distribution. |
| **Workspace & Settings** | `/settings` | Team invitations, RBAC roles, security audits, AI provider settings, audit logging. |

---

## 4. Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Bundler**: Vite 6
- **Styling**: Tailwind CSS with custom Peacock-inspired palette (`#009F98`, `#102C46`)
- **Icons**: Lucide React
- **Export Engines**: jsPDF, html2canvas, docx, SheetJS (xlsx)
- **Testing**: Vitest & React Testing Library

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM & DB**: SQLAlchemy 2.0 (AsyncIO) with asyncpg & PostgreSQL
- **Analytical Query Engine**: DuckDB (in-memory embedded SQL engine)
- **Data Serialization**: Apache Parquet & PyArrow
- **Migrations**: Alembic
- **AI Integrations**: Google Gemini API (`google-genai` / `gemini-3.1-flash-lite`), Local Ollama (`gemma3:4b`), and Deterministic fallback engines
- **Validation**: Pydantic v2
- **Testing**: pytest, pytest-asyncio, anyio

---

## 5. System Architecture Overview

```
                      +---------------------------------------+
                      |       React 18 + Vite Frontend        |
                      |   Tailwind CSS / Lucide / Recharts   |
                      +-------------------+-------------------+
                                          | HTTP / REST (JWT + CSRF)
                                          v
                      +---------------------------------------+
                      |         FastAPI REST Backend          |
                      |  Auth, Workspaces, RBAC, Rate Limits  |
                      +---------+-------------------+---------+
                                |                   |
            +-------------------+--+             +--+-------------------+
            |  PostgreSQL Database |             |    DuckDB Engine     |
            | Metadata, Users,     |             | Vectorized Queries,  |
            | Dashboards, Audits   |             | Parquet Aggregations |
            +----------------------+             +----------+-----------+
                                                            |
                                                 +----------v-----------+
                                                 | Storage Data Root    |
                                                 | Immutable Parquet    |
                                                 | Files & Manifests    |
                                                 +----------------------+
```

---

## 6. Project Folder Structure

```
DataLens/
├── backend/                        # FastAPI Python backend application
│   ├── alembic/                    # Database migrations
│   ├── app/
│   │   ├── api/v1/                 # REST API route handlers
│   │   │   └── endpoints/          # Endpoint controllers (auth, datasets, dashboards, etc.)
│   │   ├── core/                   # Configuration, security, logging, exceptions
│   │   ├── db/                     # Database engine & session factories
│   │   ├── dependencies/           # FastAPI dependency injection (auth, RBAC)
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   └── services/               # Core business logic (analytics, AI, ingestion)
│   ├── scripts/                    # Maintenance & verification scripts
│   ├── tests/                      # Pytest backend test suite
│   ├── alembic.ini                 # Alembic configuration
│   └── pyproject.toml              # Python dependencies & tools config
├── src/                            # React TypeScript frontend
│   ├── components/                 # Reusable UI widgets, layout, topnav, sidebar
│   ├── context/                    # React Context (Auth, Theme, Navigation)
│   ├── pages/                      # Page components (dashboards, ask, data, reports)
│   ├── services/                   # API clients, export services, storage helpers
│   ├── tests/                      # Frontend Vitest test suite
│   ├── App.tsx                     # Main router and route declarations
│   └── main.tsx                    # React application entrypoint
├── docs/                           # Architectural, UI/UX, and deployment guides
├── .env.example                    # Template environment variables
├── .gitignore                      # Git exclusion rules
├── package.json                    # Frontend package dependencies & scripts
├── tailwind.config.js              # Tailwind CSS styling configuration
├── vite.config.ts                  # Vite build configuration
└── README.md                       # Root documentation
```

---

## 7. Prerequisites

Before installing, ensure the following are installed on your machine:
- **Node.js**: v18.0.0 or higher (v20+ recommended)
- **npm** or **pnpm**
- **Python**: v3.11, v3.12, or v3.13
- **PostgreSQL**: v15, v16, or v17 running locally or via Docker
- **Git**

---

## 8. Backend Installation & Startup

### Step 1: Create and activate a Python virtual environment
```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# On Linux/macOS:
source .venv/bin/activate
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
# or via pip directly
pip install -e .
```

### Step 3: Run the FastAPI development server
```bash
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## 9. Frontend Installation & Startup

### Step 1: Install Node packages
```bash
# In the project root directory:
npm install
```

### Step 2: Start the Vite development server
```bash
npm run dev
```
The application will open at [http://localhost:5173](http://localhost:5173).

---

## 10. PostgreSQL Database Setup

1. Start your PostgreSQL service.
2. Create the `datalens` database:
```sql
CREATE DATABASE datalens;
```
3. Ensure your PostgreSQL user has read/write privileges on the database.

---

## 11. Environment Variable Configuration

Create a `.env` file in the `backend/` directory by copying `.env.example`:

```bash
cp .env.example backend/.env
```

Configure your environment settings:
```ini
APP_NAME="DataLens API"
APP_ENV="development"
DEBUG=true
API_V1_PREFIX="/api/v1"

# Database Connection
DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@127.0.0.1:5432/datalens"

# CORS Allowed Origins
CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

# Security
SECRET_KEY="replace_with_a_long_random_secret_string"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# File Storage
STORAGE_ROOT="./storage_data"
MAX_UPLOAD_SIZE_MB=50

# AI Provider Configuration (Google Gemini)
AI_PROVIDER="gemini"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
GEMINI_MODEL="gemini-3.1-flash-lite"
AI_ENABLED=true
AI_SEND_SAMPLE_VALUES=false
```

---

## 12. Database Migrations (Alembic)

Run database migrations to initialize or update the schema:

```bash
cd backend
alembic upgrade head
```

To create a new migration after updating SQLAlchemy models:
```bash
alembic revision --autogenerate -m "describe_changes"
```

---

## 13. Running Automated Tests

### Backend Unit & Integration Tests (pytest)
```bash
# From the backend directory with virtual environment active:
pytest backend/tests -v
```

### Frontend Component & Service Tests (Vitest)
```bash
# From the project root:
npm test
# or single run:
npx vitest run
```

---

## 14. Production Build Instructions

### Build Frontend
```bash
npm run build
```
The optimized production bundle will be generated in `dist/`.

### Run Backend in Production Mode
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 4
```

---

## 15. Deployment Overview

- **Frontend**: Can be served via NGINX, Cloudflare Pages, Vercel, or Netlify from the compiled `dist/` directory.
- **Backend**: Can be hosted on Railway, Render, AWS ECS, or standard Ubuntu VPS via Docker or systemd with Gunicorn/Uvicorn workers.
- **Database**: Managed PostgreSQL (AWS RDS, Supabase, Neon, or self-hosted).
- **Storage**: Local filesystem or mounted EBS volume specified by `STORAGE_ROOT`.

---

## 16. Security & Governance Notes

- **Zero Raw Data to External AI**: Only column profiles and anonymized schemas are sent to external AI providers; raw dataset rows are computed deterministically on-premise using DuckDB.
- **CSRF & Cookie Protection**: Authentication utilizes HTTP-only refresh cookies with CSRF double-submit token validation.
- **Tenant Isolation**: All queries enforce strict workspace ID isolation across datasets, dashboards, and audit logs.
- **Sanitized Secrets**: No production secrets, database credentials, or API keys are committed to source control.

---

## License

Proprietary © DataLens AI Platform. All rights reserved.
