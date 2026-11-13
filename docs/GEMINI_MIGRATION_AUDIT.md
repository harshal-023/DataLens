# DataLens — Complete Gemini Migration Architecture Audit

## 1. Executive Summary

This audit identifies all integration points, dependencies, components, and security considerations required to migrate the DataLens application from the OpenAI API to Google's official Gemini API (`google-genai`).

Gemini will become the primary and sole active external LLM provider across all DataLens AI capabilities:
1. **Ask Your Data** (`AIAnalyticsOrchestrator` natural language intent parsing and plan generation).
2. **Business Insight Engine** (`BusinessInsightEngine` for statistical & ML interpretations).
3. **Prompt Lab & Playground** (`PromptExecutionService` for user prompt execution and evaluation).
4. **Prompt Evaluation & Experiments** (`PromptEvaluator` for model-assisted evaluation).
5. **Phase 3C Advanced Analytics** (narrative synthesis for anomalies, forecasts, and customer segments).

---

## 2. Existing OpenAI Integration Points

| File Path | Integration Role | Observed Implementation Details | Required Migration Action |
| :--- | :--- | :--- | :--- |
| `backend/app/core/config.py` | Configuration | `AI_PROVIDER: str = "openai"`, `AI_MODEL = "gpt-4o-mini"`, `AI_API_KEY = ""` | Change default to `AI_PROVIDER = "gemini"`, `GEMINI_MODEL = "gemini-2.5-flash"`, support `GEMINI_API_KEY` (with fallback to `AI_API_KEY`). |
| `backend/app/services/ai/base.py` | Provider Interface | Abstract class with `check_availability`, `generate_plan`, `generate_explanation`. | Expand interface to provide generic `generate_text` / `execute_prompt` so consumer services do not access client internals. |
| `backend/app/services/ai/factory.py` | Provider Factory | Instantiates `OpenAIProvider` when `provider == "openai"`. | Instantiate `GeminiProvider` by default. Remove OpenAI from active factory routes. |
| `backend/app/services/ai/openai_provider.py` | Vendor Provider | Uses `openai.AsyncOpenAI` client. | Superseded by `backend/app/services/ai/gemini_provider.py`. |
| `backend/app/services/ml/insights.py` | ML Business Insights | Line 33: checks `isinstance(provider, OpenAIProvider)` and calls `provider.client.chat.completions.create` directly. | Refactor to call `provider.generate_text()` or `provider.generate_structured()` polymorphically. |
| `backend/app/services/prompt_lab/execution_service.py` | Prompt Execution | Line 53: checks `isinstance(live_provider, OpenAIProvider)` and calls `live_provider.client.chat.completions.create`. | Refactor to invoke `live_provider.generate_text()` polymorphically with Gemini token tracking. |
| `backend/app/services/prompt_lab/evaluator.py` | Experiment Evaluation | Model-assisted evaluation heuristic. | Connect to `GeminiProvider` for live AI judging when configured. |
| `src/pages/prompt-lab/PromptLabOverview.tsx` | Frontend UI | Hardcoded `gpt-4o-mini` default model and `<option value="openai">`. | Replace with `gemini-2.5-flash`, `gemini-2.5-pro` and `<option value="gemini">Google Gemini</option>`. |
| `src/pages/prompt-lab/ExperimentDetail.tsx` | Frontend UI | Default model `gpt-4o-mini`. | Update default to `gemini-2.5-flash`. |
| `backend/pyproject.toml` | Python Dependencies | `openai>=1.50.0` listed in dependencies. | Add `google-genai>=1.0.0` to dependencies. |
| `.env.example` | Env Template | `AI_PROVIDER="openai"`, `AI_API_KEY=""`. | Update to `AI_PROVIDER="gemini"`, `GEMINI_API_KEY=""`, `GEMINI_MODEL="gemini-2.5-flash"`. |

---

## 3. High-Priority Architectural Findings

1. **Leaky Abstraction in Consumer Services:**
   In `backend/app/services/ml/insights.py` and `backend/app/services/prompt_lab/execution_service.py`, code directly performed `isinstance(provider, OpenAIProvider)` and called `provider.client.chat.completions.create`.
   *Solution:* We must formalize `generate_text()` and `generate_structured()` on the `AIProvider` base class. This ensures all consumer services remain 100% decoupled from any vendor SDK specifics.

2. **Official Google GenAI SDK Usage:**
   Per requirements, we must use the new official `google-genai` package (`from google import genai` and `genai.Client(api_key=...)`) rather than legacy `google-generativeai`.

3. **Structured Outputs with Gemini:**
   Gemini 2.5 Flash natively supports structured JSON generation via `response_mime_type="application/json"` and `response_schema` (or JSON formatting instructions). This fits cleanly with DataLens's `AnalyticalPlan` schema.

4. **Security & Privacy:**
   - The API key (`GEMINI_API_KEY`) is stored strictly server-side in `backend/.env`.
   - `AI_SEND_SAMPLE_VALUES=false` ensures only column names, inferred types, and deterministic calculation aggregates are sent to the LLM. Raw data records remain inside DuckDB / Parquet.

---

## 4. Migration Plan & Sequence

1. **Stage 1:** Install `google-genai`, implement `GeminiProvider`, update `base.py` and `factory.py`.
2. **Stage 2:** Update environment configurations in `config.py` and `.env.example`.
3. **Stage 3:** Set Gemini as default, eliminate active OpenAI execution paths.
4. **Stage 4:** Integrate Gemini with Ask Your Data, Business Insight Engine, Prompt Lab, and Phase 3C Advanced Analytics.
5. **Stage 5:** Verify security boundaries and data minimization.
6. **Stage 6:** Update API status endpoint and frontend references.
7. **Stage 7 & 8:** Comprehensive pytest test suite + Live verification.
8. **Stage 9 & 10:** Documentation and final regression audit.

