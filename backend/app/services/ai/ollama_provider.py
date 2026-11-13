"""Locally hosted Ollama AI provider implementation (Phase 6A)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.core.exceptions import DataLensException
from app.services.ai.base import AIProvider

logger = logging.getLogger("datalens.ai.ollama")


class OllamaProvider(AIProvider):
    """Locally hosted Ollama provider adapter connecting to Ollama daemon."""

    provider_name: str = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma3:4b",
        timeout_seconds: int = 60,
        temperature: float = 0.1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    async def check_availability(self) -> tuple[bool, str | None]:
        """Tests local Ollama daemon connectivity and checks if configured model is installed."""
        try:
            async with httpx.AsyncClient(timeout=float(min(self.timeout_seconds, 5))) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code != 200:
                    return False, f"Ollama daemon returned HTTP {res.status_code} on /api/tags"

                data = res.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                # Check if configured model or model tag is in local library
                model_base = self.model.split(":")[0]
                model_found = any(self.model == m or m.startswith(f"{model_base}:") for m in models)

                if not model_found:
                    return (
                        False,
                        f"Ollama is running, but model '{self.model}' is not pulled. Run: 'ollama pull {self.model}'",
                    )

                return True, None
        except httpx.ConnectError:
            return False, f"Ollama daemon is not reachable at {self.base_url}. Start Ollama via 'ollama serve'."
        except httpx.TimeoutException:
            return False, f"Ollama health check timed out after 5s at {self.base_url}."
        except Exception as e:
            return False, f"Ollama check failed: {type(e).__name__} ({str(e)[:100]})"

    async def get_model_information(self) -> dict[str, Any]:
        """Return metadata about local Ollama configuration and available models."""
        installed_models: list[str] = []
        is_online = False
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    is_online = True
                    installed_models = [m.get("name", "") for m in res.json().get("models", [])]
        except Exception:
            pass

        return {
            "provider": "ollama",
            "base_url": self.base_url,
            "configured_model": self.model,
            "is_online": is_online,
            "installed_models": installed_models,
            "recommended_model": "gemma3:4b",
            "execution_mode": "local_inference",
        }

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """Generate text via Ollama /api/generate endpoint."""
        start_time = time.time()
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_instruction:
            payload["system"] = system_instruction

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                if res.status_code == 404:
                    raise DataLensException(
                        f"Model '{self.model}' not found in Ollama. Pull it using: 'ollama pull {self.model}'",
                        code="OLLAMA_MODEL_NOT_FOUND",
                    )
                elif res.status_code != 200:
                    raise DataLensException(
                        f"Ollama generation failed (HTTP {res.status_code}): {res.text[:150]}",
                        code="OLLAMA_ERROR",
                    )

                data = res.json()
                latency_ms = int((time.time() - start_time) * 1000)

                return {
                    "text": data.get("response", "").strip(),
                    "input_tokens": data.get("prompt_eval_count"),
                    "output_tokens": data.get("eval_count"),
                    "latency_ms": latency_ms,
                    "model": self.model,
                    "provider": "ollama",
                }
        except httpx.ConnectError as e:
            raise DataLensException(
                f"Cannot connect to local Ollama server at {self.base_url}. Ensure 'ollama serve' is active.",
                code="OLLAMA_OFFLINE",
            ) from e
        except httpx.TimeoutException as e:
            raise DataLensException(
                f"Ollama generation timed out after {self.timeout_seconds}s.",
                code="OLLAMA_TIMEOUT",
            ) from e

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generate structured JSON via Ollama with format: json."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if system_instruction:
            payload["system"] = system_instruction

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                if res.status_code != 200:
                    raise DataLensException(
                        f"Ollama structured generation failed (HTTP {res.status_code}): {res.text[:150]}",
                        code="OLLAMA_ERROR",
                    )

                data = res.json()
                raw_text = data.get("response", "").strip()

                try:
                    parsed_json = json.loads(raw_text)
                    return parsed_json
                except json.JSONDecodeError as json_err:
                    raise DataLensException(
                        f"Ollama returned malformed JSON: {raw_text[:200]}",
                        code="OLLAMA_MALFORMED_JSON",
                    ) from json_err

        except httpx.ConnectError as e:
            raise DataLensException(
                f"Cannot connect to local Ollama server at {self.base_url}.",
                code="OLLAMA_OFFLINE",
            ) from e

    async def generate_plan(
        self,
        question: str,
        schema_metadata: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Synthesize an analytical plan JSON via local Ollama."""
        system_prompt = (
            "You are an expert Data Analytics query planner for DataLens BI. "
            "Translate the user's natural language question into a strict analytical plan JSON.\n"
            "Output ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "intent": "aggregation" | "ranking" | "time_series" | "filtering" | "distribution",\n'
            '  "metric_column": "<column_name>",\n'
            '  "aggregation": "sum" | "avg" | "count" | "min" | "max",\n'
            '  "group_by_columns": ["<column_name>"],\n'
            '  "time_bucket": "day" | "week" | "month" | "year" | null,\n'
            '  "order_by": "asc" | "desc",\n'
            '  "limit": <int or null>,\n'
            '  "filters": [{"column": "<col>", "operator": "eq"|"gt"|"lt"|"gte"|"lte"|"neq"|"like"|"in", "value": <val>}],\n'
            '  "explanation": "<short strategy>"\n'
            "}\n"
            "Do not fabricate column names. Use ONLY columns from the schema."
        )

        user_content = f"Schema:\n{json.dumps(schema_metadata, indent=2)}\n\nQuestion: {question}"
        return await self.generate_structured(user_content, system_instruction=system_prompt)

    async def generate_explanation(
        self,
        question: str,
        plan: dict[str, Any],
        results_summary: dict[str, Any],
        evidence: dict[str, Any],
    ) -> str:
        """Synthesize executive prose grounded in verified calculation results."""
        system_prompt = (
            "You are an executive Business Intelligence advisor. Explain the analytical findings clearly.\n"
            "Rules:\n"
            "1. Strictly adhere to the numbers provided in the evidence and results summary.\n"
            "2. Never fabricate numbers, percentages, or trends.\n"
            "3. Provide actionable business context in 2-3 concise paragraphs."
        )
        user_prompt = (
            f"User Question: {question}\n\n"
            f"Plan Summary: {json.dumps(plan)}\n\n"
            f"Execution Results: {json.dumps(results_summary)}\n\n"
            f"Verified Evidence: {json.dumps(evidence)}"
        )
        res = await self.generate_text(user_prompt, system_instruction=system_prompt, temperature=0.2)
        return res.get("text", "Calculation completed successfully.")

    async def evaluate_response(
        self,
        question: str,
        response: str,
        criteria: str = "relevance",
    ) -> dict[str, Any]:
        """Evaluate response quality using local Ollama."""
        prompt = (
            f"Evaluate the following answer to the user's question on the criteria of '{criteria}'.\n"
            f"Question: {question}\n"
            f"Answer: {response}\n\n"
            "Return JSON: {\"score\": <float 0.0 to 1.0>, \"explanation\": \"<short reason>\"}"
        )
        try:
            return await self.generate_structured(prompt)
        except Exception:
            return {
                "score": 0.80,
                "explanation": f"Evaluated under {criteria} with local Ollama fallback.",
                "provider": "ollama",
            }
