# DataLens – Immutable Enterprise Audit Logging & Hash Chaining

## 1. Overview
The Enterprise Audit Logging platform records an immutable, chronologically ordered, tamper-evident log of all significant mutations, authentications, and administrative events occurring across DataLens.

---

## 2. Event Payload Schema
Each audit record captures:
- `id` (UUID)
- `workspace_id` (UUID nullable)
- `actor_id` & `actor_email`
- `action` (e.g., `custom_role_created`, `dataset_governance_updated`, `resource_policy_revoked`)
- `resource_type` & `resource_id`
- `timestamp` (UTC)
- `ip_address` & `user_agent`
- `correlation_id`
- `outcome` (`SUCCESS`, `FAILURE`, `DENIED`)
- `metadata_snapshot` (Sanitized with zero secret leakage)
- `previous_hash` & `chained_hash`

---

## 3. Cryptographic Chained Hash Specification
To detect retroactive database row modifications, row deletions, or arbitrary injections, each record incorporates the hash of the immediately preceding record:

$$\text{chained\_hash}_i = \text{SHA256}(\text{id}_i \,\|\, \text{previous\_hash}_{i-1} \,\|\, \text{action}_i \,\|\, \text{outcome}_i \,\|\, \text{timestamp}_i)$$

- **Genesis Record**: The initial record links to `"GENESIS_DATALENS_ROOT_HASH"`.
- **Validation**: `GovernanceService.verify_audit_chain()` walks sequential records and validates that $\text{chained\_hash}_i$ matches recalculated values and links accurately to $\text{previous\_hash}_{i+1}$.

---

## 4. API Endpoints
- `GET /api/v1/audit-logs`: Search and filter audit records with date range and outcome filters.
- `GET /api/v1/audit-logs/export`: Download full audit logs as CSV.

