# DataLens — AI Provider Architecture

## 1. Architectural Philosophy

DataLens enforces strict decoupling between **analytical calculations** and **generative AI interpretations**:

```
                       ┌────────────────────────┐
                       │  User Question / Form  │
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │ Google Gemini Provider │
                       │    (Plan Inference)    │
                       └───────────┬────────────┘
                                   │ AnalyticalPlan (JSON)
                                   ▼
                       ┌────────────────────────┐
                       │ DuckDB & Python ML     │
                       │ (Deterministic Compute)│
                       └───────────┬────────────┘
                                   │ Verified Metrics & Evidence
                                   ▼
                       ┌────────────────────────┐
                       │ Google Gemini Provider │
                       │ (Grounded Explanation) │
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │ Verified BI Response   │
                       └────────────────────────┘
```

1. **No Code Execution by LLM:** Gemini never generates or executes arbitrary SQL or Python code. It maps business questions to schema-constrained, strongly validated JSON analytical plans (`AnalyticalPlan`).
2. **Deterministic Mathematical Authority:** All mathematical computations, aggregations, forecasting calculations, and statistical outlier formulas are calculated exclusively by DuckDB, NumPy, SciPy, and Scikit-Learn.
3. **Factual Grounding:** Gemini is strictly supplied with verified calculation results to produce executive prose. It is prohibited from fabricating numbers, metrics, or causal assumptions.

---

## 2. Provider Abstraction Interface (`AIProvider`)

Located in [`backend/app/services/ai/base.py`](file:///d:/PE%20CP/backend/app/services/ai/base.py), the `AIProvider` abstract class standardizes all AI operations:

```python
class AIProvider(ABC):
    @abstractmethod
    async def check_availability(self) -> tuple[bool, str | None]:
        """Tests provider connectivity without leaking credentials."""
        pass

    @abstractmethod
    async def generate_plan(
        self,
        question: str,
        schema_metadata: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Translates user natural language into a validated JSON analytical plan."""
        pass

    @abstractmethod
    async def generate_explanation(
        self,
        question: str,
        plan: dict[str, Any],
        results_summary: dict[str, Any],
        evidence: dict[str, Any],
    ) -> str:
        """Explains verified calculation results in executive business prose."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """Executes a prompt with token usage accounting and latency measurement."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generates validated structured JSON matching instructions."""
        pass
```

---

## 3. Concrete Implementations

### 3.1 `GeminiProvider`
- **SDK:** Official `google-genai` Python library (`genai.Client`).
- **Asynchronous Execution:** Fully non-blocking async operations via `client.aio.models.generate_content`.
- **Model:** Default `gemini-2.5-flash` (also supports `gemini-2.5-pro`).
- **Structured Output:** Native JSON support via `response_mime_type="application/json"`.
- **Resilience:** Automatic exponential backoff for transient 429 and 503 errors.

### 3.2 `DisabledAIProvider`
- Provides immediate deterministic fallback when `AI_ENABLED=false` or when `GEMINI_API_KEY` is not provisioned.
- Guarantees zero system crashes, allowing all data exploration, dashboard visualization, and manual analysis to proceed uninterrupted.

