# Phase 7A: Security, Governance & Reliability Audit

## 1. Authentication & Token Management
- **Password Hashing**: Implements **Argon2id** (`argon2-cffi`), with memory cost $= 65,536 \text{ KiB}$, time cost $= 3$ iterations, and parallelism $= 4$ lanes. Null, empty, and sub-8-character passwords are strictly rejected.
- **JWT Architecture**:
  - Algorithm strictly pinned to `HS256` (header tampered with `none` or asymmetric algs is rejected).
  - Short-lived Access Tokens (15 minutes).
  - Refresh Tokens (7 days) stored as SHA-256 hashes in `refresh_sessions` with explicit revocation and device fingerprinting.
  - Multi-session support with `/api/v1/sessions/revoke-others` functionality.

---

## 2. Authorization & RBAC
- **Built-in Roles**: `OWNER`, `ADMIN`, `EDITOR`, `VIEWER`.
- **Granular Permission Catalog**: 24 discrete permissions governing datasets, dashboards, transformations, reports, members, and connections.
- **Resource Access Policies**: Allows fine-grained override per resource (e.g., granting a Viewer access to export a specific report or revoking dataset edit permissions from a specific Editor).
- **Workspace Tenant Boundaries**: All SQL queries filter explicitly on `workspace_id`. Cross-tenant data leaks are prevented via repository-level filters and database foreign key cascades.

---

## 3. Cryptography & Data Protection
- **External Connector Credentials**: Encrypted at rest in `data_source_connections.encrypted_credentials` using **AES-256-GCM** with unique nonces and cryptographic salts.
- **Shareable Links**:
  - Secure random tokens (`secrets.token_urlsafe(32)`).
  - Password protection hashed via Argon2id.
  - Configurable expiration timestamps and download count limits.
- **SSRF Protection on Connectors**:
  - Connector hostnames are resolved and validated against loopback, link-local, and private cloud metadata IP ranges (`127.0.0.0/8`, `169.254.169.254`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) prior to opening external network sockets.

---

## 4. Query Safety & Code Execution Protections
- **DuckDB Compilation**: Natural Language Analytics and Transformation pipelines compile queries through an AST (Abstract Syntax Tree) whitelist.
- **Arbitrary Code Blocked**: Expressions containing `__import__`, `eval`, `exec`, `subprocess`, `os`, `sys`, system functions, or raw SQL semicolons are blocked and logged.
- **Path Traversal Guard**: All Parquet read/write operations resolve paths relative to the designated dataset root and assert `os.path.commonpath` constraints to block `../` directory traversal attacks.

---

## 5. AI Privacy & Hallucination Guardrails
- **Data Classification Filtering**: Datasets classified as `CONFIDENTIAL` or `RESTRICTED` enforce `local_only_enforced = True`, strictly routing to Ollama or deterministic fallback and blocking transmission to Google Gemini.
- **Zero Raw Rows to Cloud AI**: AI prompts receive only high-level schema metadata, column statistical distributions, and approved metric formulas. No raw table rows are ever included in prompt context.
- **Hallucination Verification**: `NLAEvidenceVerifier` inspects all numbers cited in AI narratives against computed evidence cards. Any ungrounded percentage or quantity triggers an immediate warning flag and reverts to verified deterministic values.

---

## 6. Audit Logging & Non-Repudiation
- **Cryptographic Hash Chaining**: `enterprise_audit_logs` records include `prev_record_hash` and `record_hash` (SHA-256 calculated across actor, action, target, timestamp, and previous hash).
- **Tamper Evidence**: Any alteration to historical audit rows breaks the cryptographic chain, surfacing integrity violations during security export audits.

