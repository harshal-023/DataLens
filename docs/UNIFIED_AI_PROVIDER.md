# DataLens Phase 6A – Unified AI Provider Interface Specification

---

## 1. Architectural Contract (`AIProvider`)

All artificial intelligence and language model features in DataLens consume the abstract `AIProvider` contract (`backend/app/services/ai/base.py`).

Application modules (Ask Your Data, Prompt Lab, Automated Report Writer, Machine Learning Insights) are decoupled from vendor-specific SDKs.

```python
class AIProvider(ABC):
    @abstractmethod
    async def check_availability(self) -> tuple[bool, str | None]: ...

    @abstractmethod
    async def get_model_information(self) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_plan(
        self,
        question: str,
        schema_metadata: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_explanation(
        self,
        question: str,
        plan: dict[str, Any],
        results_summary: dict[str, Any],
        evidence: dict[str, Any],
    ) -> str: ...

    async def evaluate_response(
        self,
        question: str,
        response: str,
        criteria: str = "relevance",
    ) -> dict[str, Any]: ...
```

---

## 2. Standardized Response Format

Text generation produces normalized telemetry dictionaries across all providers:
```json
{
  "text": "Revenue grew 14% quarter-over-quarter...",
  "input_tokens": 145,
  "output_tokens": 62,
  "latency_ms": 312,
  "model": "gemini-3.5-flash",
  "provider": "gemini"
}
```

---

## 3. Supported Implementations

1. **`GeminiProvider`:** Powered by the official Google Gen AI SDK (`google-genai`).
2. **`OllamaProvider`:** Powered by local Ollama REST API (`http://localhost:11434`).
3. **`DeterministicAIProvider`:** 100% offline heuristic rule engine guaranteeing zero crash when LLMs are unconfigured or unavailable.

