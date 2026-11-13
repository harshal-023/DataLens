# DataLens – Data Access Governance & Sensitive Column Masking

## 1. Overview
The Data Access Governance platform provides fine-grained sensitivity classification, export controls, and column-level masking across all analytical datasets in DataLens.

---

## 2. Sensitivity Classification Tiers
1. **`PUBLIC`**: Unrestricted data suitable for general distribution.
2. **`INTERNAL`**: Standard internal operational data accessible to all workspace members.
3. **`CONFIDENTIAL`**: Sensitive business data; exports restricted by default.
4. **`RESTRICTED`**: Highly confidential (PII, financial, health records); requires column suppression and explicit clearance.

---

## 3. Sensitive Column Masking Schemes
- **`redact`**: Completely masks values with bullets (`"••••••••"`).
- **`hash`**: Computes one-way cryptographic SHA-256 hash digests, preserving joinability while hiding raw values.
- **`partial`**: Masks all but the last 4 characters (e.g. `***-**-1234` or `j***@domain.com`).

---

## 4. Administrative Verification & Enforcement
- Suggested column classifications require explicit administrative confirmation before taking effect.
- Applied automatically across previews, exports, Ask Your Data responses, and transformations unless the user possesses the `governance:bypass` permission or is workspace Owner.

---

## 5. API Endpoints
- `GET /api/v1/governance/datasets/{dataset_id}`: Retrieve dataset sensitivity and column mask configurations.
- `PUT /api/v1/governance/datasets/{dataset_id}`: Update classification and column masking rules.

