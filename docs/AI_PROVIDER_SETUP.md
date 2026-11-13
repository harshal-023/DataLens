# DataLens — AI Provider Setup & Configuration Guide

## 1. Overview

DataLens features a decoupled, vendor-agnostic AI provider layer designed to translate business questions into structured analytical plans and generate executive explanations of verified calculations.

The core architecture strictly decouples the application from vendor-specific SDKs via the `AIProvider` abstract base class (`app/services/ai/base.py`).

---

## 2. Environment Variables

Configure the following variables in `backend/.env`:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `AI_ENABLED` | boolean | `true` | Globally enables or disables AI integration. When `false`, the system uses deterministic heuristic fallback. |
| `AI_PROVIDER` | string | `openai` | AI backend provider. Currently supported: `openai`. Extensible to `anthropic`, `gemini`, or `local`. |
| `AI_API_KEY` | string | `""` | Vendor API key (e.g., `sk-...`). **Never commit this to version control.** |
| `AI_MODEL` | string | `gpt-4o-mini` | Model identifier used for plan generation and narrative explanation. |
| `AI_TIMEOUT_SECONDS` | integer | `30` | Per-request timeout in seconds for provider calls. |
| `AI_MAX_RETRIES` | integer | `2` | Number of automated exponential backoff retries on transient errors. |

---

## 3. Provider Architecture

### 3.1 Factory Pattern (`AIProviderFactory`)

`AIProviderFactory.get_provider()` dynamically instantiates the appropriate provider:
- If `AI_ENABLED=false` or `AI_API_KEY` is not set: returns `DisabledAIProvider`.
- If `AI_PROVIDER=openai`: returns `OpenAIProvider`.
- Any unconfigured provider raises a structured `DataLensException(code="UNSUPPORTED_AI_PROVIDER")`.

### 3.2 Offline & Fallback Mode (`DisabledAIProvider`)

When AI is unconfigured or disabled:
1. `check_availability()` returns `(False, "AI features are currently disabled in configuration.")`.
2. `generate_plan()` raises `DataLensException(code="AI_DISABLED")`.
3. The `AIAnalyticsOrchestrator` catches `AI_DISABLED` and immediately switches to deterministic keyword heuristics (`_heuristic_plan_fallback`).
4. DuckDB performs 100% of the analytical computation.
5. Narrative explanations fall back to verified fact-based summaries.

---

## 4. Operational Health & Readiness

Test AI connectivity at any time via the authenticated endpoint:

```http
GET /api/v1/ai/status
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

### Example Response:
```json
{
  "ai_enabled": true,
  "provider": "openai",
  "model": "gpt-4o-mini",
  "operational": true,
  "error": null
}
```

> **Security Note:** The status endpoint never includes the `AI_API_KEY` or sensitive credentials in the response payload or error messages.

