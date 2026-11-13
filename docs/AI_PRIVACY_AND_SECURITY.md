# AI Privacy, Data Governance & Security Controls

## 1. Zero Raw Data Invariant
DataLens is engineered with an uncompromising architectural guarantee:
**Raw dataset rows are NEVER transmitted to external Cloud AI providers.**

### What Is Sent to Cloud AI (Gemini):
1. **Sanitized Table Schemas:** Column names, standard data types (e.g., `VARCHAR`, `BIGINT`, `TIMESTAMP`), and nullability constraints.
2. **Aggregated Statistics:** Non-sensitive aggregate metrics (e.g., count of records, sum of revenue, min/max date ranges) necessary to formulate an analytical hypothesis.
3. **User Business Prompts:** The natural-language inquiry entered by the user.

### What Is Kept Strictly Local:
- All row-level records, PII, individual transaction details, customer names, email addresses, and Parquet data files remain exclusively within the local DuckDB analytics engine or PostgreSQL database.

---

## 2. Sensitivity Classification & Enforcement

DataLens classifies datasets into four governance tiers:
1. `PUBLIC`: Non-sensitive reference data (e.g., public calendars, open benchmarks).
2. `INTERNAL`: Standard business data (e.g., internal KPIs, operational metrics).
3. `CONFIDENTIAL`: Business-sensitive records (e.g., customer account lists, financial statements).
4. `RESTRICTED`: Highly-regulated records (e.g., HIPAA, GDPR, PII, PCI-DSS data).

### Governance Rules:
- If a dataset is tagged **`CONFIDENTIAL`** or **`RESTRICTED`**, DataLens's `HybridAIRouter` automatically blocks external cloud egress.
- Requests involving these tiers are processed exclusively on **Local Ollama** or the offline **Deterministic Engine**.
- Any attempt to force a cloud route on restricted data raises an immediate `HTTP 403 Forbidden: Cloud AI egress prohibited for classified dataset`.

---

## 3. Workspace-Level AI Privacy Policies
Admins can define workspace-wide security boundaries stored in the `ai_privacy_policies` table:
- **`cloud_ai_permitted` (Boolean):** Master switch allowing or disallowing external cloud models.
- **`local_ai_enforced` (Boolean):** Forces all queries across all team members to use on-premises Ollama models.
- **`mask_column_names` (Boolean):** Automatically hashes or pseudonyms column identifiers before prompt compilation.
- **`anonymize_aggregates` (Boolean):** Applies differential privacy noise or threshold suppression to small aggregate buckets.

---

## 4. Secret & Token Scrubbing
Before any payload leaves the application boundary to an AI model (cloud or local), the sanitization pipeline removes:
- Database connection strings (`postgresql://...`, `mysql://...`).
- Cloud storage keys and access tokens (`AKIA...`, `Bearer ...`).
- Passwords, API secrets, and internal IP addresses.

