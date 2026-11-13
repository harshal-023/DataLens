# DataLens — Phase 4 Known Limitations

## Overview

This document outlines known operational boundaries, design constraints, and technical considerations identified during the comprehensive integration audit of Phase 4.

---

## 1. External AI Rate Limits & Quotas
- **Google Gemini Free Tier Rate Limits**: When using free-tier Gemini API keys, burst requests or high-frequency automated batch report generation may exceed the per-minute quota (`429 Quota Exceeded`).
- **Mitigation & Handling**: DataLens implements a fully verified, deterministic algorithmic fallback (`DeterministicNarrativeGenerator`). If Gemini fails or times out, report generation automatically falls back to rule-based mathematical synthesis with zero user disruption or data cell leakage.

---

## 2. In-Memory DuckDB Concurrency
- **File Locks & Concurrency**: DuckDB operates in read-only or in-process mode per request. Simultaneous multi-user heavy queries on the exact same derived Parquet file rely on operating system page caching.
- **Scaling Recommendation**: For enterprise workloads exceeding 100 million rows, external object stores (S3/GCS) paired with partitioned Parquet manifests or a clustered analytical engine should be considered.

---

## 3. Email Delivery Adapter
- **Development vs. Production**: The platform currently provides a built-in development file/log email adapter (`dev_email_adapter`) for auditing outgoing messages.
- **Production SMTP**: For external live email delivery to customer inboxes, configure production SMTP gateway credentials (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS`) in the environment configuration.

---

## 4. Attachment Size Constraints
- **25 MB Email Ceiling**: Corporate mail transfer agents (MTAs) routinely reject attachments larger than 25MB.
- **Handling**: Generated PDF, DOCX, XLSX, and CSV reports exceeding 25MB are stored locally in DataLens object storage, and an authenticated direct download URL is inserted into the email body rather than attaching the oversized file directly.

