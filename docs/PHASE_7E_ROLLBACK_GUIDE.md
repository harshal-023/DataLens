# DataLens Phase 7E: Production Rollback & Recovery Guide

## 1. Objective & Philosophy

This document outlines the standard operating procedures for executing a safe, deterministic rollback of the DataLens platform in the event of an operational anomaly, deployment failure, database migration incompatibility, or data corruption incident.

The DataLens architecture is fundamentally designed around **immutable data artifacts**:
- Uploaded and derived datasets are persisted as immutable Parquet versions on disk.
- Transformations and imports generate new dataset versions without overwriting existing versions.
- As a result, rollback procedures do not require destructive file reversals; rather, pointer reversion and point-in-time state recovery are utilized.

---

## 2. Rollback Triggers & Decision Matrix

A rollback must be evaluated and initiated if any of the following critical thresholds are breached during or immediately following deployment:

| Severity Level | Trigger Condition | Decision Action | Authorized Personnel |
| :---: | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Readiness probe (`/api/v1/health/ready`) fails consistently for $> 3$ minutes. | Immediate full application rollback to previous release. | Lead DevOps / Release Commander |
| **SEV-1 (Critical)** | Database migration failure causing table locks or API 500 errors $> 5\%$. | Immediate container pause + database transaction rollback. | Lead Database Administrator |
| **SEV-2 (High)** | Query latency degradation $> 300\%$ over baseline on standard analytical queries. | Shift traffic to previous cluster version / blue-green switch. | Lead Backend Architect |
| **SEV-2 (High)** | Data corruption detected in Parquet partition generation or DuckDB queries failing. | Revert API image to prior build; flag corrupted versions as inactive. | Lead Data Engineer |
| **SEV-3 (Moderate)** | Frontend UI rendering regression or routing defect in non-critical module. | Revert static frontend assets; backend remains active. | Frontend Lead |

---

## 3. Step-by-Step Rollback Procedures

### Scenario A: Application Layer Rollback (API & Frontend Only)
*Use this procedure when database schema migrations were backward-compatible or no migration was run.*

1. **Stop Current Ingress Traffic**:
   Switch load balancer / reverse proxy upstream to the standby (previous) release instance.
2. **Revert Frontend Static Assets**:
   ```bash
   # Re-link webroot to previous stable release bundle
   sudo ln -sfn /var/www/datalens/releases/v1.0.0-stable /var/www/datalens/html
   sudo systemctl reload nginx
   ```
3. **Revert Backend API Containers / Services**:
   ```bash
   # If using systemd / direct binary:
   sudo systemctl stop datalens-api datalens-worker
   sudo ln -sfn /opt/datalens/releases/v1.0.0-stable /opt/datalens/backend
   sudo systemctl start datalens-api datalens-worker

   # If using Docker / Kubernetes:
   kubectl rollout undo deployment/datalens-api -n datalens
   kubectl rollout undo deployment/datalens-worker -n datalens
   ```
4. **Verify Health**:
   ```bash
   curl -f http://127.0.0.1:8000/api/v1/health/ready
   ```

---

### Scenario B: Database Schema Rollback (Alembic Downgrade)
*Use this procedure when a newly applied database migration fails or introduces an incompatibility.*

1. **Pause Background Worker & Schedulers**:
   ```bash
   sudo systemctl stop datalens-worker
   ```
2. **Determine Target Migration Revision**:
   ```bash
   cd /opt/datalens/backend
   source .venv/bin/activate
   alembic current
   # Identify previous revision hash (e.g. 7c3d2e1a9b8f)
   ```
3. **Execute Controlled Downgrade**:
   ```bash
   alembic downgrade -1
   # Or to specific stable revision:
   alembic downgrade <PREVIOUS_REVISION_HASH>
   ```
4. **Verify Schema Parity**:
   Run schema inspection scripts to ensure all tables, constraints, and indexes match the target revision.
5. **Resume Application & Workers**:
   ```bash
   sudo systemctl restart datalens-api datalens-worker
   ```

---

### Scenario C: Disaster Recovery / Full Cold Restore (Point-In-Time)
*Use this procedure in catastrophic incidents involving severe data corruption or hardware loss.*

1. **Stop Application Cluster**:
   ```bash
   sudo systemctl stop datalens-api datalens-worker nginx
   ```
2. **Restore PostgreSQL Database**:
   ```bash
   # Provision fresh target database or drop corrupted database
   dropdb -h $DB_HOST -U postgres datalens
   createdb -h $DB_HOST -U postgres datalens

   # Restore verified binary dump
   pg_restore -h $DB_HOST -U postgres -d datalens -v /backups/postgres/datalens_backup_latest.dump
   ```
3. **Restore Parquet & Artifact Storage Snapshot**:
   ```bash
   # Extract matching storage snapshot to ensure relational metadata matches physical files
   sudo tar -xzf /backups/storage/storage_data_latest.tar.gz -C /var/lib/datalens/
   sudo chown -R datalens:datalens /var/lib/datalens/storage
   ```
4. **Execute Disaster Recovery Verification Drill**:
   ```bash
   python /opt/datalens/backend/scripts/backup_restore_drill.py
   ```
5. **Start Services & Validate Ingress**:
   ```bash
   sudo systemctl start datalens-api datalens-worker nginx
   curl -s http://127.0.0.1:8000/api/v1/health/ready | jq .
   ```

---

## 4. Post-Rollback Postmortem & Communications

1. **Incident Logging**:
   Record exact timestamp, triggering conditions, executed commands, and affected tenants in the Incident Management System.
2. **Stakeholder Notification**:
   Notify workspace owners and platform administrators regarding platform stabilization.
3. **RCA (Root Cause Analysis)**:
   Conduct blameless postmortem within 24 hours to identify root causes and update automated regression tests to prevent recurrence.

