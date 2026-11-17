# DataLens 1.0 – Step-by-Step Free Cloud Deployment Guide

## 1. Overview

This guide provides end-to-end instructions for deploying DataLens 1.0 to a production-grade cloud environment at **₹0 per month** using:
1. **Neon Serverless PostgreSQL** (Database)
2. **Render Free Web Service** (FastAPI Backend)
3. **Cloudflare Pages** (Vite + React Frontend)

---

## 2. Prerequisites
- A free GitHub account.
- A free [Neon](https://neon.tech) account (no credit card required).
- A free [Render](https://render.com) account (no credit card required).
- A free [Cloudflare](https://dash.cloudflare.com) account (no credit card required).

---

## 3. Step-by-Step Deployment Instructions

### Step 1: Provision Free Serverless PostgreSQL on Neon
1. Log in to [Neon Console](https://console.neon.tech).
2. Click **Create Project**.
3. Name the project `datalens-production` and select PostgreSQL 16. Choose a region closest to your users.
4. Neon will provide your connection string:
   ```text
   postgresql://datalens_owner:npg_xyz123@ep-frosty-pine-123456.us-east-2.aws.neon.tech/datalens?sslmode=require
   ```
5. Transform this into the async format required by SQLAlchemy `asyncpg`:
   ```text
   postgresql+asyncpg://datalens_owner:npg_xyz123@ep-frosty-pine-123456.us-east-2.aws.neon.tech/datalens?ssl=require
   ```
   *(Keep this connection string ready for Step 2).*

---

### Step 2: Deploy Backend to Render Free Web Service
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Web Service**.
3. Connect your GitHub repository containing the DataLens codebase.
4. Configure the Web Service settings:
   - **Name**: `datalens-api`
   - **Region**: Choose the same region as your Neon database.
   - **Branch**: `main` (or `master`)
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command**:
     ```bash
     gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
     ```
   - **Instance Type**: **Free** (512 MB RAM, 0.1 vCPU).
5. Open the **Environment Variables** tab and add the following:
   - `APP_NAME`: `DataLens BI Platform`
   - `APP_ENV`: `production`
   - `DEBUG`: `false`
   - `DATABASE_URL`: *[Your asyncpg connection string from Step 1]*
   - `SECRET_KEY`: *[Generate using `python -c "import secrets; print(secrets.token_hex(32))"`]*
   - `CORS_ORIGINS`: `https://datalens.pages.dev,http://localhost:5173` *(Update with your exact Cloudflare Pages URL in Step 3)*
   - `AI_PROVIDER`: `deterministic` *(or `gemini` if you have a free Google AI Studio key)*
   - `AI_ENABLED`: `true`
   - `AI_SEND_SAMPLE_VALUES`: `false`
   - `STORAGE_ROOT`: `/tmp/datalens_storage`
6. Click **Create Web Service**.
7. Render will build dependencies, run all Alembic migrations (`alembic upgrade head`), and start the application.
8. Note your public backend URL (e.g., `https://datalens-api.onrender.com`).

---

### Step 3: Deploy Frontend to Cloudflare Pages
1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com).
2. Navigate to **Compute (Workers & Pages)** $\rightarrow$ **Create Application** $\rightarrow$ **Pages** $\rightarrow$ **Connect to Git**.
3. Select your GitHub repository.
4. Configure build settings:
   - **Framework preset**: `Vite`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
   - **Root directory**: `/` (repository root)
5. Under **Environment variables (Advanced)**, add:
   - `VITE_API_URL`: `https://datalens-api.onrender.com` *(Your Render backend URL from Step 2)*
6. Click **Save and Deploy**.
7. Cloudflare will install dependencies, compile 1,934 modules, and deploy static assets to their global edge network.
8. Your frontend will be live at `https://<your-project>.pages.dev`.

---

### Step 4: Finalize CORS Configuration
1. Return to Render Dashboard $\rightarrow$ `datalens-api` $\rightarrow$ **Environment**.
2. Update `CORS_ORIGINS` to match your exact Cloudflare Pages domain:
   ```text
   CORS_ORIGINS="https://<your-project>.pages.dev"
   ```
3. Save changes. Render will automatically re-deploy in $< 30$ seconds.

---

## 4. Verification & Health Probes

Test the live deployment from terminal:

1. **Liveness Probe**:
   ```bash
   curl -I https://datalens-api.onrender.com/api/v1/health
   # Returns: HTTP/2 200 ok
   ```
2. **Readiness Probe**:
   ```bash
   curl -s https://datalens-api.onrender.com/api/v1/health/ready | jq .
   # Expected output:
   # {
   #   "status": "ready",
   #   "service": "datalens-api",
   #   "components": {"database": "connected"}
   # }
   ```
3. **Frontend Application**:
   Navigate to `https://<your-project>.pages.dev` in your browser.
   - Register a new account.
   - Upload a CSV or Excel spreadsheet.
   - Verify statistical profiling and automated data quality scoring.
   - Create a dashboard with charts and filters.
   - Execute an AI Autonomous Insight audit.
   - Export an executive report in PDF format.

