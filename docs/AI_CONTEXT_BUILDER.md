# AI Semantic Context Builder

## 1. Overview
The [`AIContextBuilder`](file:///d:/PE%20CP/backend/app/services/intelligence/context_builder.py) bridges the Business Semantic Layer and DataLens AI interactions. It prepares structured, token-budgeted prompt contexts for Ask Your Data, Business Reports, and ML Insights without exposing raw dataset records.

---

## 2. Injected Semantic Information

When a user asks a question in **Ask Your Data** (e.g., *"What was our total revenue last quarter by region?"*), `AIContextBuilder` enriches the prompt with:
1. **Dataset Overview:** Dataset name, row count, quality score (`quality_score/100`).
2. **Business Domain & Purpose:** Identified domain (`SALES`, `FINANCE`, etc.) and analytical purpose.
3. **Column Semantics & Glossary:**
   - Physical column name and business name (`order_id` as `'Order ID'`).
   - Logical type (`string`, `float`, `date`) and semantic type (`currency`, `customer_identifier`).
   - Role (`[PRIMARY_KEY]`, `[MEASURE]`, `[DIMENSION]`).
   - Suggested default aggregation (`SUM`, `AVG`, `COUNT_DISTINCT`).
   - Format mask (`USD`, `INR`, `PERCENT`).
4. **Approved Business Metrics:** List of registered metric formulas (e.g. `Average Order Value = Revenue / Total Orders`).
5. **Confirmed Data Relationships:** Discovered and confirmed foreign key links (`orders.customer_id -> customers.customer_id`).
6. **Data Quality Warnings:** Noted data limitations (e.g. high missingness, date boundaries).

---

## 3. Privacy & Token Bounds

- **Zero Raw Data Transmission:** Only metadata, business names, column definitions, and mathematical aggregates are provided. Raw data rows are strictly omitted.
- **Column Context Limits:** Budgeted to `MAX_COLUMNS_IN_CONTEXT = 40` prioritized by Primary Keys, Measures, and key Dimensions.
- **Metric Context Limits:** Budgeted to `MAX_METRICS_IN_CONTEXT = 15` approved metrics.
- **Privacy Policy Egress Enforcement:** For datasets marked `CONFIDENTIAL` or `RESTRICTED`, the router blocks Cloud Gemini egress and ensures prompt evaluation occurs locally via Ollama or the offline deterministic engine.

