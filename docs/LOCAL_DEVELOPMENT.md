# DataLens — Local Development Guide

Complete guide for running the DataLens frontend and backend concurrently in local development.

---

## 1. Prerequisites

- **Node.js:** v18+ (verified with v20+)
- **Python:** 3.12 or 3.13 (verified with Python 3.13.2)
- **PostgreSQL:** 16 (on port 5432)

---

## 2. Backend Setup & Startup

1. **Navigate to `backend` and create virtualenv:**
   ```powershell
   cd "d:\PE CP\backend"
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e .
   ```

2. **Configure `.env`:**
   ```powershell
   Copy-Item .env.example .env
   ```

3. **Run database migrations:**
   ```powershell
   python -m alembic upgrade head
   ```

4. **Start the FastAPI backend server:**
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   API Docs available at: `http://127.0.0.1:8000/docs`

---

## 3. Frontend Setup & Startup

1. **Install dependencies:**
   ```powershell
   cd "d:\PE CP"
   npm install
   ```

2. **Start the Vite development server:**
   ```powershell
   npm run dev
   ```
   Application available at: `http://localhost:5173`

---

## 4. Running Verification Test Suites

```powershell
# Backend pytest suite (unit + parity + security + reports)
cd "d:\PE CP\backend"
.\.venv\Scripts\python.exe -m pytest -v

# Python linting
.\.venv\Scripts\python.exe -m ruff check .

# Frontend production build & typecheck
cd "d:\PE CP"
npm run build
```

