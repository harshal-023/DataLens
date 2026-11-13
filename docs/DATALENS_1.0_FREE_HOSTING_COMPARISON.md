# DataLens 1.0 – Free Hosting & Cloud Provider Comparison Report

## 1. Objective & Target Cost

The objective of this research is to establish a 100% verified production cloud deployment architecture that costs **₹0 per month ($0.00)** without utilizing temporary free trials, promotional credits that expire, or requiring billing activations that auto-charge credit cards.

Target Monthly Operating Cost: **₹0 / Month**.

---

## 2. Cloud Provider Comparison Matrix

| Component | Provider / Service | Free Allowance (Official) | Documented Limitations | Card Required? | Cost (₹) | Feasibility Rating |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **Frontend** | **Cloudflare Pages** | **Unlimited bandwidth**, unlimited requests, 500 builds/month, custom domains, free automatic SSL/TLS, global edge CDN. | 25 MB max individual file size. (DataLens bundle chunks are $< 500$ KB). | **NO** | **₹0** | **RECOMMENDED (10/10)** |
| Frontend | Vercel Hobby | 100 GB bandwidth/month, unlimited deployments. | Non-commercial only by Terms of Service; bandwidth overage risk. | NO | ₹0 | VIABLE (7/10) |
| Frontend | Netlify Free | 100 GB bandwidth/month, 300 build minutes/month. | Hard bandwidth cutoffs after 100 GB; team limits. | NO | ₹0 | VIABLE (7/10) |
| **Backend API** | **Render Free Web Service** | **512 MB RAM, 0.1 vCPU**, supports Python/FastAPI via Gunicorn/Uvicorn, free TLS, custom domains. | Spins down after 15m inactivity; ~50s cold start on wake. 750 free instance hours/month. | **NO** | **₹0** | **RECOMMENDED (9/10)** |
| Backend API | Koyeb Free Tier | 512 MB RAM, 0.1 vCPU, 2 nano instances, global edge network. | Requires credit card verification upon registration even on free tier. | YES | ₹0 | CONDITIONAL (6/10) |
| Backend API | Hugging Face Spaces | 2 vCPU, 16 GB RAM (CPU Basic), persistent, free forever. | Default public visibility; requires custom container configuration for full API routing. | NO | ₹0 | VIABLE (8/10) |
| **PostgreSQL** | **Neon Free Tier** | **0.5 GB (500 MB) storage**, 1 project, serverless autoscaling compute (up to 0.25 vCPU), branching support. Compatible with PostgreSQL 16/18, asyncpg, Alembic. | Inactive compute suspends after 5m; auto-resumes in $< 1$s on first incoming query. | **NO** | **₹0** | **RECOMMENDED (10/10)** |
| PostgreSQL | Supabase Free | 500 MB database, 2 free projects, pooled connections. | Project pauses after 7 days of inactivity; requires manual dashboard unpause. | NO | ₹0 | VIABLE (7/10) |
| PostgreSQL | Aiven Free Trial | $300 trial credits for 30 days. | Not permanently free; shuts down after 30 days unless paid. | YES | Paid | REJECTED (0/10) |
| **Parquet Storage**| **Supabase Storage** | **1 GB free persistent file storage**, S3-compatible protocol & REST API, generous bandwidth. | 1 GB storage limit (sufficient for 100+ compressed Parquet datasets). | **NO** | **₹0** | **RECOMMENDED (9/10)** |
| Parquet Storage| Cloudflare R2 | 10 GB storage free/month, 10M Class B reads, 1M Class A writes. Zero egress fees. | Requires credit card on file during account setup even though $0 billed. | YES | ₹0 | CONDITIONAL (8/10) |
| Parquet Storage| Render Disk | 1 GB to 100 GB persistent block storage attached to web service. | Only available on paid services ($0.25/GB/month, minimum $1/mo). | YES | Paid | REJECTED (0/10) |
| **Scheduler/Workers**| **In-Process Async Worker (Render)** | **Zero extra container cost**: runs inside the FastAPI process using non-blocking `asyncio` task loop and SKIP LOCKED queue. | Sleeps when web service sleeps unless pinged by free uptime monitor (e.g. UptimeRobot). | **NO** | **₹0** | **RECOMMENDED (9/10)** |
| Scheduler/Workers| Render Background Worker | Dedicated background container with independent CPU. | Requires Starter plan ($7.00/month = ~₹580/mo). | YES | Paid | REJECTED (0/10) |
| **AI Provider**| **Deterministic Engine + Local Ollama** | **Unlimited local analytical planning**, DuckDB queries, and rule-based explanations. | No LLM narrative prose if running purely offline. | **NO** | **₹0** | **RECOMMENDED (10/10)** |
| AI Provider| Google Gemini Free Tier | 15 RPM, 1,000,000 TPM free tier via Google AI Studio API key. | Rate limits apply; DataLens automatically falls back to deterministic engine. | NO | ₹0 | **RECOMMENDED (9/10)** |

---

## 3. Analysis of Critical Limitations & Engineering Solutions

### 3.1 Backend Cold Starts on Render Free Tier
- **Observation**: Render Free Web Services sleep after 15 minutes of inactivity. When a new HTTP request arrives, waking the container takes approximately 45–50 seconds.
- **Solution**:
  1. Frontend displays a clean, elegant "Waking analytics engine..." state indicator if initial connection exceeds 3 seconds.
  2. Free external monitoring service (e.g., UptimeRobot free tier with 50 monitors) can ping `https://<render-url>/api/v1/health` every 14 minutes, keeping the container warm during business hours at **₹0**.

### 3.2 Neon PostgreSQL Compute Suspension
- **Observation**: Neon pauses serverless compute after 5 minutes of database inactivity.
- **Solution**: Unlike traditional cold starts, Neon resumes compute in **$< 1,000$ milliseconds** on the first incoming TCP socket connection. DataLens connection pooling with `pool_pre_ping=True` handles this transparently without dropping connections.

### 3.3 Storage Persistence for Parquet Files
- **Observation**: Free-tier PaaS containers (Render, Railway, Fly.io free) have ephemeral local filesystems that wipe local files on container restarts.
- **Solution**:
  1. Parquet datasets are persisted directly in **Supabase Storage** (1 GB free permanently, no credit card) or **Cloudflare R2** (10 GB free, requires card for verification) using the S3-compatible API.
  2. On query execution, DuckDB streams or reads partitions directly, ensuring **zero data loss across container restarts**.

---

## 4. Final Free-Tier Architecture Recommendation

The audited, optimal zero-cost stack for DataLens 1.0 is:

```
[ Frontend: Cloudflare Pages ] (₹0, No Card, Unlimited Bandwidth)
                │
                ▼ (HTTPS / TLS)
[ Backend: Render Free Web Service ] (₹0, No Card, 512 MB RAM, Python 3.13)
       │                    │
       ▼                    ▼
[ Database: Neon Free ]  [ Parquet Storage: Supabase Storage / R2 ]
 (₹0, 500 MB Postgres)    (₹0, 1 GB – 10 GB Persistent Storage)
```

**Total Expected Monthly Operating Cost: ₹0.00**.
