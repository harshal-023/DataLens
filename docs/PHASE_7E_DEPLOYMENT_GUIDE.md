# DataLens Phase 7E: Production Deployment Guide

## 1. Architecture Overview

DataLens is designed as a cloud-native, modular Business Intelligence platform. Its production topology separates static web serving, high-performance API handling, transactional state storage, and analytical query compute:

```
[ Internet / Clients ]
         │
         ▼
[ Edge CDN / WAF / Cloudflare ]
         │
    ┌────┴──────────────────────────┐
    ▼                               ▼
[ Frontend Web ]            [ API Reverse Proxy ]
  (Nginx / S3)              (Nginx / Traefik / Envoy)
                                    │
                                    ▼
                      [ FastAPI Backend Cluster ]
                      (Gunicorn + Uvicorn Workers)
                         │              │
         ┌───────────────┘              └────────────────┐
         ▼                                               ▼
[ PostgreSQL 16+ Cluster ]                     [ High-Performance Storage ]
  - Relational Metadata                          - Parquet Partitions (NVMe / EFS)
  - SKIP LOCKED Job Queue                        - Embedded DuckDB Query Engine
  - Chained Audit Logs                           - Report Artifact Cache
         ▲
         │
[ Dedicated Scheduler / Worker Daemon ]
  - Single Scheduler Instance
  - Background Job Processor
```

---

## 2. Infrastructure Requirements

### 2.1 Sizing Guidelines

| Component | Minimum (Small Team $\le 50$ Users) | Recommended (Enterprise $\le 500$ Users) | High Throughput ($> 500$ Users) |
| :--- | :--- | :--- | :--- |
| **API Servers** | 2 vCPU, 4 GB RAM (2 instances) | 4 vCPU, 8 GB RAM (3–5 instances) | 8 vCPU, 16 GB RAM (Auto-scaling cluster) |
| **PostgreSQL** | 2 vCPU, 4 GB RAM, 50 GB SSD | 4 vCPU, 16 GB RAM, 250 GB NVMe | 8 vCPU, 32 GB RAM, 1 TB NVMe (Read Replicas) |
| **Parquet Storage** | 100 GB Fast SSD | 500 GB Shared NVMe / AWS EFS | Multi-Terabyte High IOPS SAN / AWS EFS Max IOPS |
| **Worker Process** | 2 vCPU, 4 GB RAM (1 instance) | 4 vCPU, 8 GB RAM (2 instances) | 8 vCPU, 16 GB RAM (Dedicated worker pool) |

---

## 3. Step-by-Step Production Deployment

### Step 1: Provision and Configure PostgreSQL
1. Deploy PostgreSQL 16 or 18 on dedicated cloud infrastructure (e.g., AWS RDS PostgreSQL, Google Cloud SQL, or self-hosted cluster).
2. Tune PostgreSQL `postgresql.conf`:
   ```ini
   max_connections = 200
   shared_buffers = 4GB
   effective_cache_size = 12GB
   maintenance_work_mem = 1GB
   checkpoint_completion_target = 0.9
   wal_buffers = 16MB
   default_statistics_target = 100
   random_page_cost = 1.1
   effective_io_concurrency = 200
   work_mem = 32MB
   min_wal_size = 2GB
   max_wal_size = 16GB
   ```
3. Create dedicated application user and database:
   ```sql
   CREATE DATABASE datalens;
   CREATE USER datalens_app WITH ENCRYPTED PASSWORD 'StrongProductionPassword';
   GRANT ALL PRIVILEGES ON DATABASE datalens TO datalens_app;
   ```

### Step 2: Configure Shared Parquet Storage
1. Mount a shared, high-throughput POSIX-compliant volume (AWS EFS, Azure Files NFS, or local NVMe array) to `/var/lib/datalens/storage`.
2. Ensure read/write permissions for the application runtime user:
   ```bash
   sudo mkdir -p /var/lib/datalens/storage/datasets
   sudo mkdir -p /var/lib/datalens/storage/reports
   sudo chown -R datalens:datalens /var/lib/datalens/storage
   sudo chmod -R 750 /var/lib/datalens/storage
   ```

### Step 3: Run Database Migrations (Alembic)
Before launching API services, execute all Alembic migrations to update the database schema:
```bash
cd /opt/datalens/backend
source .venv/bin/activate
export DATABASE_URL="postgresql+asyncpg://datalens_app:StrongProductionPassword@db.internal:5432/datalens"
alembic upgrade head
```

### Step 4: Deploy FastAPI Application (Gunicorn + Uvicorn)
1. Install production dependencies:
   ```bash
   python -m venv /opt/datalens/backend/.venv
   /opt/datalens/backend/.venv/bin/pip install --upgrade pip setuptools wheel
   /opt/datalens/backend/.venv/bin/pip install -r /opt/datalens/backend/requirements.txt
   /opt/datalens/backend/.venv/bin/pip install gunicorn uvicorn[standard]
   ```
2. Configure Systemd service `/etc/systemd/system/datalens-api.service`:
   ```ini
   [Unit]
   Description=DataLens Business Intelligence Backend API
   After=network.target

   [Service]
   User=datalens
   Group=datalens
   WorkingDirectory=/opt/datalens/backend
   EnvironmentFile=/etc/datalens/backend.env
   ExecStart=/opt/datalens/backend/.venv/bin/gunicorn app.main:app \
       --workers 4 \
       --worker-class uvicorn.workers.UvicornWorker \
       --bind 0.0.0.0:8000 \
       --timeout 120 \
       --graceful-timeout 30 \
       --keep-alive 5 \
       --access-logfile /var/log/datalens/access.log \
       --error-logfile /var/log/datalens/error.log

   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
3. Start and enable service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now datalens-api
   ```

### Step 5: Deploy Dedicated Background Worker & Scheduler
To prevent duplicate job execution, run exactly **one** scheduler process:
1. Configure Systemd service `/etc/systemd/system/datalens-worker.service`:
   ```ini
   [Unit]
   Description=DataLens Dedicated Background Worker & Scheduler
   After=network.target datalens-api.service

   [Service]
   User=datalens
   Group=datalens
   WorkingDirectory=/opt/datalens/backend
   EnvironmentFile=/etc/datalens/backend.env
   ExecStart=/opt/datalens/backend/.venv/bin/python -m app.services.automation.worker_daemon

   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
2. Start and enable worker:
   ```bash
   sudo systemctl enable --now datalens-worker
   ```

### Step 6: Build and Deploy Frontend (Nginx)
1. Build production static bundle:
   ```bash
   cd /opt/datalens/frontend
   npm ci
   npm run build
   # Outputs optimized static files into dist/
   ```
2. Deploy `dist/` to web root `/var/www/datalens/html`.
3. Configure Nginx virtual host `/etc/nginx/sites-available/datalens.conf`:
   ```nginx
   server {
       listen 80;
       server_name datalens.yourcompany.com;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl http2;
       server_name datalens.yourcompany.com;

       ssl_certificate /etc/letsencrypt/live/datalens.yourcompany.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/datalens.yourcompany.com/privkey.pem;
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;

       # Security Headers
       add_header X-Frame-Options "DENY" always;
       add_header X-Content-Type-Options "nosniff" always;
       add_header X-XSS-Protection "1; mode=block" always;
       add_header Referrer-Policy "strict-origin-when-cross-origin" always;
       add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;" always;

       root /var/www/datalens/html;
       index index.html;

       # Frontend Single Page Application fallback
       location / {
           try_files $uri $uri/ /index.html;
       }

       # Backend API Proxy
       location /api/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 120s;
           client_max_body_size 100M;
       }

       # Health probe endpoint
       location /health {
           proxy_pass http://127.0.0.1:8000/api/v1/health;
       }
   }
   ```
4. Test and reload Nginx:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

---

## 4. Verification & Health Probes

Verify the deployed cluster:
1. **Liveness Probe**:
   ```bash
   curl -I https://datalens.yourcompany.com/api/v1/health
   # Returns HTTP 200 {"status": "ok", "service": "datalens-api"}
   ```
2. **Readiness Probe**:
   ```bash
   curl -s https://datalens.yourcompany.com/api/v1/health/ready
   # Returns HTTP 200 {"status": "ready", "components": {"database": "connected"}}
   ```
3. **Frontend Ingestion**:
   Navigate to `https://datalens.yourcompany.com` and verify registration, login, and workspace loading.

