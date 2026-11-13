# Google Gemini Integration Architecture

## 1. Overview
DataLens integrates Google Gemini models via the modern Google Gen AI SDK (`google-genai`). The integration acts as the primary cloud reasoning engine for advanced business intelligence tasks, natural language-to-DuckDB SQL synthesis, deep analytical explanations, multi-section business report writing, and Prompt Lab prompt engineering evaluation.

---

## 2. SDK & Authentication
- **Official Library:** `google-genai` (replacing legacy deprecated `google-generativeai`).
- **Client Instantiation:**
  ```python
  from google import genai
  client = genai.Client(api_key=settings.GEMINI_API_KEY)
  ```
- **Configuration:**
  - `GEMINI_API_KEY`: Sourced securely from environment variables (`.env`). Never exposed to frontend clients or stored in the database.
  - `GEMINI_MODEL`: Defaults to `gemini-2.5-flash` (or user-configurable `gemini-1.5-pro` for deep reasoning).
  - `GEMINI_TEMPERATURE`: Tuned to `0.1` for deterministic analytical plans and code generation, up to `0.4` for narrative summaries.

---

## 3. Core Capabilities in `GeminiProvider`
The [`GeminiProvider`](file:///d:/PE%20CP/backend/app/services/ai/gemini_provider.py) implements the abstract [`AIProvider`](file:///d:/PE%20CP/backend/app/services/ai/base.py) interface:

1. **`health_check()`**:
   - Verifies network connectivity and API key validity by querying model metadata or issuing a low-overhead token check.
   - Reports latency in milliseconds and provider status (`healthy` or `unreachable`).

2. **`generate_text(prompt, system_instruction, temperature, max_output_tokens)`**:
   - Issues `client.models.generate_content(...)` with optional `GenerateContentConfig`.
   - Returns sanitized text, model identifier, execution latency, and token consumption statistics.

3. **`generate_structured_output(prompt, schema_class, ...)`**:
   - Enforces JSON response schema using `response_mime_type="application/json"` and Pydantic schema validation.
   - Automatically repairs or falls back if malformed JSON is returned.

4. **`generate_analysis_plan(user_query, schema_context, ...)`**:
   - Produces structured [`AnalysisPlan`](file:///d:/PE%20CP/backend/app/services/ai/schemas.py) including DuckDB SQL queries, chart recommendations, and filter parameters.

5. **`explain_results(query, sql, results_summary, schema_context)`**:
   - Generates executive business summaries and action points based strictly on computed aggregate numbers.

6. **`evaluate_response(prompt, response, ground_truth, criteria)`**:
   - Provides quantitative multi-metric grading (accuracy, clarity, relevance, hallucination-risk) for the Prompt Lab experiment engine.

---

## 4. Privacy & Context Minimization
- **Zero Raw Data Transmission:** Only schema metadata (column names, DuckDB types, non-sensitive min/max aggregates) and user queries are passed to Gemini. Raw row-level records are never transmitted.
- **Redaction of Secrets:** Connection strings, passwords, auth tokens, and session headers are scrubbed prior to dispatch.
- **Policy Egress Gate:** When a dataset is tagged `CONFIDENTIAL` or `RESTRICTED`, or when workspace policy has `cloud_ai_permitted=False`, Gemini calls are blocked by the [`HybridAIRouter`](file:///d:/PE%20CP/backend/app/services/ai/hybrid_router.py) and seamlessly redirected to local Ollama or the offline deterministic engine.

---

## 5. Resilience & Rate Limiting
- **Exponential Backoff:** Retries 429 and 503 HTTP responses with progressive jitter.
- **Circuit Breaker:** If 3 consecutive failures occur, the router marks Gemini temporarily degraded and cascades down to local models without crashing the user session.
