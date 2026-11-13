# DataLens – Phase 5C Architecture: Enterprise Governance, Advanced RBAC & Security Audit Platform

## 1. Executive Summary & Objective
Phase 5C extends DataLens into an enterprise-grade governance platform. It introduces granular permission controls, customizable administrative roles, resource-level access policies (RLAC), dataset sensitivity classifications, sensitive column suppression/masking, immutable tamper-evident audit logs, security event monitoring, active session revocation, and workspace security policies.

---

## 2. Granular Permissions Architecture
Permissions are defined as structured string tokens (`resource:action`):

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Granular Permissions                           │
├──────────────────────┬─────────────────────────┬───────────────────────┤
│ Dataset              │ Data Sources            │ Transformations       │
│ • dataset:view       │ • datasource:manage     │ • transformation:cr...│
│ • dataset:create     │                         │ • transformation:ex...│
│ • dataset:edit       │                         │                       │
│ • dataset:delete     │                         │                       │
│ • dataset:export     │                         │                       │
├──────────────────────┼─────────────────────────┼───────────────────────┤
│ Dashboards           │ Reports                 │ Administration        │
│ • dashboard:view     │ • report:generate       │ • member:manage       │
│ • dashboard:create   │ • report:download       │ • workspace:configure │
│ • dashboard:share    │ • report:share          │ • comment:manage      │
├──────────────────────┼─────────────────────────┼───────────────────────┤
│ Security & Governance│ Audit Logs              │ Policies              │
│ • governance:manage  │ • audit:view            │ • security_policy:... │
│ • governance:bypass  │                         │                       │
└──────────────────────┴─────────────────────────┴───────────────────────┘
```

### System Roles vs. Custom Roles
1. **System Roles (Protected)**:
   - `owner`: Universal privileges + non-transferable authority. Owner cannot be locked out or demoted.
   - `admin`: All administrative and operational permissions except deleting the workspace or removing the owner.
   - `editor`: Creation and manipulation of analytical assets (datasets, dashboards, reports, transformations, discussions).
   - `viewer`: Read-only analytical access. Cannot edit, export, or manage configurations.
2. **Custom Roles**:
   - Workspace administrators can define fine-grained roles (e.g., "Data Steward", "External Auditor", "Report Consumer") with tailored subsets of granular permissions.

---

## 3. Resource-Level Access Control (RLAC) Precedence Engine

Access evaluation follows an explicit 4-tier decision hierarchy:

```
[ Incoming Request for Resource (e.g. Dataset / Dashboard / Report) ]
                           │
                           ▼
              Is Actor Workspace Owner? ───(YES)──► [ ALLOW ]
                           │ (NO)
                           ▼
          Is there an Explicit Resource DENY? ───(YES)──► [ DENY ]
                           │ (NO)
                           ▼
          Is there an Explicit Resource GRANT? ───(YES)──► [ ALLOW ]
                           │ (NO)
                           ▼
     Does Actor's Role have the Granular Permission?
             ├── (YES) ──► [ ALLOW ]
             └── (NO)  ──► [ DENY ]
```

---

## 4. Data Governance & Column Masking Pipeline
Datasets are classified into 4 sensitivity tiers:
- **`PUBLIC`**: Freely shareable without restriction.
- **`INTERNAL`**: Standard organization data accessible to workspace members.
- **`CONFIDENTIAL`**: Sensitive business data; exports restricted by default.
- **`RESTRICTED`**: Highly confidential; restricted columns masked and downloads restricted.

### Column Masking Schemes
- **`redact`**: Masked completely with bullet dots (`"••••••••"`).
- **`hash`**: Cryptographic one-way SHA-256 hash.
- **`partial`**: Redacts all but last 4 characters (e.g. `***-**-1234`).

---

## 5. Immutable Enterprise Audit Logging & Chained Hash Verification
Every significant operational, authentication, and administrative event is recorded in `enterprise_audit_logs`.
- **Zero Secrets Redaction**: Passwords, tokens, API keys, and connection credentials are scrubbed.
- **Tamper-Evident Chained Hash**:
  $$\text{chained\_hash}_i = \text{SHA256}(\text{id}_i \,\|\, \text{previous\_hash}_{i-1} \,\|\, \text{action}_i \,\|\, \text{outcome}_i \,\|\, \text{timestamp}_i)$$
- **Guarantees & Limitations**: The hash chain detects record tampering, reordering, and unauthorized insertions. However, if an administrator directly modifies both the record and recalculates subsequent hash entries in the raw database, cryptographic immutability requires external append-only log sinks (e.g., AWS CloudWatch / S3 Object Lock).

---

## 6. Session Management & Security Policies
- User sessions are tracked in `user_sessions` with device/browser metadata and IP tracking.
- Admins and users can revoke individual sessions or "Revoke All Other Sessions".
- Workspace security policies enforce restrictions on public links, maximum link lifetimes, session timeouts, and invitation domain allowlists.

