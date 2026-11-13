# DataLens — Backup & Disaster Recovery Guide

DataLens utilizes a hybrid persistence architecture:
1. **Relational metadata & user accounts:** Stored in **PostgreSQL**.
2. **Analytical files & report binaries:** Stored in the local filesystem (`storage_data/`).

A comprehensive backup must coordinate **both** storage layers to prevent orphaned metadata or missing binary files.

---

## 1. PostgreSQL Database Backup (`pg_dump`)

### Full Database Backup (Custom Compressed Format)
```powershell
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U postgres -h localhost -p 5432 -F c -b -v -f "datalens_db_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump" datalens
```

### Schema-Only Backup
```powershell
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U postgres -h localhost -p 5432 --schema-only -f "datalens_schema_only.sql" datalens
```

---

## 2. Coordinated Storage Filesystem Backup

Backup the `storage_data/` directory containing:
- Original uploaded CSV/XLSX raw files (`storage_data/uploads/`)
- Processed Parquet partitions & manifests (`storage_data/processed/`)
- Generated PDF, DOCX, XLSX, and CSV reports (`storage_data/reports/`)

```powershell
Compress-Archive -Path ".\backend\storage_data" -DestinationPath "datalens_storage_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
```

---

## 3. Disaster Recovery Restoration Procedure

### Step 1: Restore Filesystem Storage
```powershell
Expand-Archive -Path "datalens_storage_backup_YYYYMMDD_HHMMSS.zip" -DestinationPath ".\backend\storage_data" -Force
```

### Step 2: Restore Database to Fresh or Disaster-Recovery Database
```powershell
# Create fresh database target
& "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres -h localhost -p 5432 datalens_recovered

# Restore custom dump archive
& "C:\Program Files\PostgreSQL\16\bin\pg_restore.exe" -U postgres -h localhost -p 5432 -d datalens_recovered -v "datalens_db_backup_YYYYMMDD_HHMMSS.dump"
```

### Step 3: Verify Integrity After Restore
1. Start backend pointing to restored database:
   `DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/datalens_recovered"`
2. Verify:
   - User login and password verification.
   - Dataset metadata references valid Parquet part files on disk.
   - Analytical queries (DuckDB) execute against restored files.
   - Generated report download endpoints serve existing files.

