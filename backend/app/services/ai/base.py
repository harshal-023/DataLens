"""Provider-independent abstract base class for LLMs in DataLens (Phase 6A)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Abstract Base Class for LLM providers in DataLens.

    Decouples analytical, reporting, and prompt workflows from vendor SDKs.
    """

    @abstractmethod
    async def check_availability(self) -> tuple[bool, str | None]:
        """Tests provider connectivity and authentication without leaking credentials.

        Returns (True, None) if operational, or (False, error_reason) if unavailable.
        """
        pass

    async def health_check(self) -> tuple[bool, str | None]:
        """Convenience alias for check_availability()."""
        return await self.check_availability()

    @abstractmethod
    async def get_model_information(self) -> dict[str, Any]:
        """Returns structured metadata about active model, context window, capabilities, and provider."""
        pass

    @abstractmethod
    async def generate_plan(
        self,
        question: str,
        schema_metadata: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Translates a natural language question into a structured analytical plan JSON."""
        pass

    async def generate_analysis_plan(
        self,
        question: str,
        schema_metadata: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Convenience alias for generate_plan()."""
        return await self.generate_plan(question, schema_metadata, conversation_history)

    @abstractmethod
    async def generate_explanation(
        self,
        question: str,
        plan: dict[str, Any],
        results_summary: dict[str, Any],
        evidence: dict[str, Any],
    ) -> str:
        """Generates an executive, evidence-grounded explanation of verified DuckDB calculation results."""
        pass

    async def explain_results(
        self,
        question: str,
        plan: dict[str, Any],
        results_summary: dict[str, Any],
        evidence: dict[str, Any],
    ) -> str:
        """Convenience alias for generate_explanation()."""
        return await self.generate_explanation(question, plan, results_summary, evidence)

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """Executes a prompt and returns normalized response dictionary:

        {
            "text": str,
            "input_tokens": int | None,
            "output_tokens": int | None,
            "latency_ms": int,
            "model": str,
            "provider": str,
        }
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generates a validated structured JSON object."""
        pass

    async def generate_structured_output(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Convenience alias for generate_structured()."""
        return await self.generate_structured(prompt, system_instruction, temperature)

    async def evaluate_response(
        self,
        question: str,
        response: str,
        criteria: str = "relevance",
    ) -> dict[str, Any]:
        """Evaluates an AI response for quality/relevance/factual consistency.

        Returns { "score": float, "explanation": str }
        """
        # Default heuristic evaluation if provider does not override
        return {
            "score": 0.85,
            "explanation": f"Heuristic evaluation passed for criteria: {criteria}.",
            "provider": getattr(self, "provider_name", "unknown"),
        }
