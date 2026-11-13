# DataLens Phase 5C – Known Limitations & Future Architecture Considerations

This document details known limitations, architectural boundaries, edge-case trade-offs, and future scalability considerations for the Enterprise Governance, Advanced RBAC, and Security Audit platform introduced in Phase 5C.

---

## 1. Tamper-Evident Audit Hash Chain Integrity

### Limitation
The SHA-256 hash chaining mechanism guarantees cryptographic detection of in-database modifications or row deletions if an attacker or rogue administrator modifies the audit log table directly. Each row's hash is computed as:
$$\text{hash} = \text{SHA256}(\text{id} + \text{prev\_hash} + \text{action} + \text{outcome} + \text{timestamp})$$

### Boundary
- **Direct Database Modification vs. Application Validation:** While the chaining integrity can be verified via the `/api/v1/governance/audit-logs/verify` integrity scan, PostgreSQL does not inherently prevent an administrative superuser (`postgres`) from modifying both a row and recomputing all subsequent downstream hashes in a mass UPDATE query.
- **Mitigation & Future Work:**
  - For SOC2 Type II or FedRAMP high-compliance tiers, immutable cold storage streaming (e.g., AWS S3 Object Lock in Compliance Mode or Google Cloud Storage Bucket Lock) should be implemented as a write-once, read-many (WORM) target.
  - Asynchronous background workers will pipe verified hashes to an external immutable ledger or timestamping authority (RFC 3161).

---

## 2. In-Memory Security Anomaly Detection Window

### Limitation
The security anomaly burster detection engine (detecting failed login bursts, unauthorized 403 access spikes, revoked token reuse, and rapid sequential data exports) tracks IP and User ID event frequencies in-memory via sliding time-window counters.

### Boundary
- **Multi-Instance Horizontal Scaling:** When DataLens runs in a single-container or unified process deployment, in-memory counters provide zero-latency detection without additional database overhead. However, in a distributed multi-replica cluster behind an AWS ALB or Kubernetes ingress without sticky sessions, burst counts across multiple instances may not aggregate instantaneously unless backed by a centralized state store.
- **Mitigation & Future Work:**
  - Redis / Valkey distributed sliding windows via Redis sorted sets (`ZADD` with timestamps and `ZREMRANGEBYSCORE`) will be connected in Phase 5D to unify burst detection across clustered worker nodes.

---

## 3. High-Volume Dataset Column Masking & Streaming

### Limitation
Column masking (`redact`, `hash`, `partial`) is applied deterministically during query execution and preview fetching. For DuckDB analytical queries, masked columns are replaced with sanitized representations prior to serializing results to JSON or Parquet export streams.

### Boundary
- **Very Large Parquet Chunk Streaming:** When exporting multi-gigabyte datasets with billions of rows under `RESTRICTED` sensitivity, applying dynamic Python-level regex or partial transforms on every row during JSON serialization incurs CPU overhead.
- **Mitigation & Future Work:**
  - Column masking rules are pushed down directly into DuckDB SQL expressions (e.g., `CASE WHEN sensitivity='RESTRICTED' THEN '••••••••' ELSE col END`) so that C++ vectorized execution performs the masking at memory-bandwidth speeds without round-tripping through Python interpreters.

---

## 4. Email Allowlist Validation Scope

### Limitation
Workspace Security Policies include an `allowed_email_domains` configuration (e.g., `["acmecorp.com", "partner.org"]`).

### Boundary
- **Retroactive Membership:** When a workspace administrator updates the allowed email domains list, the policy strictly restricts *new* invitations and membership additions. Existing members with previously valid non-matching domains remain until manually audited or revoked by the workspace administrator.
- **Recommendation:** Run the Security Incident scanner immediately after modifying domain allowlists to highlight existing members outside the newly authorized corporate domains.

---

## 5. Offline & Development Email Delivery

### Limitation
During local automated test execution and offline development, outgoing email invitations and security alert notifications utilize the mocked email transport / local logger rather than an external SMTP or SendGrid/SES gateway.

### Boundary
- Real transactional email delivery requires setting `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD` in the `.env` production deployment environment. When unconfigured, all invite tokens and security dispatches are safely routed to system logs and mock dispatch queues.

