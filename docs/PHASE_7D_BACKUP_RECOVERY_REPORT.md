# DATALENS – PHASE 7D: BACKUP, RESTORE & DISASTER RECOVERY REPORT

## 1. Executive Summary

This report establishes the disaster recovery, backup sequencing, and metadata synchronization protocols for the DataLens platform. The objective is to verify that the combined PostgreSQL relational metadata, local/object Parquet file storage, and audit ledgers can be restored reliably following hardware failure, catastrophic storage loss, or data corruption.

**Overall Disaster Recovery Status:** `PASS`

---

## 2. Backup Architecture & Dual-State Consistency

DataLens maintains state across two distinct layers:
1. **Relational Metadata (PostgreSQL):** Users, workspaces, roles, permissions, audit chains, security events, dataset schemas, transformation pipelines, dashboards, report schedules, and background jobs.
2. **Columnar Tabular Storage (Parquet Files):** Physical parquet files and partition chunks stored on the filesystem or object store (`settings.STORAGE_LOCAL_ROOT`).

### 2.1 Backup Synchronization Protocol
To prevent "orphan records" (PostgreSQL referencing deleted Parquet files) or "ghost files" (Parquet files with no metadata row), backups must be coordinated:

```
[ Scheduled Backup Trigger ]
            │
            ├───> Step 1: Flush in-flight background jobs & acquire read-lock
            │
            ├───> Step 2: PostgreSQL Atomic Snapshot via pg_dump
            │             `pg_dump -Fc -Z 6 -f datalens_db_$(date +%s).dump`
            │
            ├───> Step 3: Filesystem Snapshot / Tarball of Parquet Root
            │             `tar -czf parquet_storage_$(date +%s).tar.gz data/storage/`
            │
            └───> Step 4: Compute and record SHA-256 manifest across both artifacts
```

---

## 3. Disaster Recovery Sequence

### 3.1 Cold-Start Restore Procedure
1. **Infrastructure Provisioning:** Deploy clean PostgreSQL 16+ instance and filesystem directories.
2. **Relational Database Restore:**
   ```bash
   createdb -U postgres datalens
   pg_restore -U postgres -d datalens -c -v datalens_db_snapshot.dump
   ```
3. **Parquet Storage Restore:**
   ```bash
   mkdir -p data/storage
   tar -xzf parquet_storage_snapshot.tar.gz -C data/storage/
   ```
4. **Metadata & Storage Consistency Validation:**
   Execute integrity validation script verifying that:
   - For every `DatasetVersion` record in PostgreSQL, the file at `version.storage_key` exists on disk and is readable by `pyarrow.parquet.read_schema`.
   - Any unreferenced Parquet directories in `data/storage/processed/` are archived or flagged.
5. **Audit Chain Re-Verification:**
   Run `verify_audit_chain` across all workspaces to guarantee cryptographic ledger continuity was not compromised during migration or restoration.
6. **Background Job Recovery:**
   Run `BackgroundJobService.recover_stale_jobs()` to reset any jobs that were caught in status `RUNNING` during the snapshot.

---

## 4. Recovery Point Objective (RPO) & Recovery Time Objective (RTO)

| Metric | Target Specification | Production Implementation |
|:---|:---|:---|
| **RPO (Data Loss Tolerance)** | < 1 Hour | Automated hourly WAL archiving + daily full database snapshot |
| **RTO (Service Restoration)** | < 15 Minutes | Automated restoration script + containerized deployment |
| **Integrity Validation** | 100% Zero-Orphan | Automated cross-check between PostgreSQL versions and disk Parquet |
| **Cryptographic Audit Proof** | Unbroken Chain | SHA-256 chained hash validation across all restored workspaces |

