"""Hybrid AI Provider Router with task-based routing, privacy governance, and fallbacks (Phase 6A)."""

from __future__ import annotations

import logging
import re
import time
from enum import StrEnum
from typing import Any

from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.fallback_provider import DeterministicAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.ollama_provider import OllamaProvider

logger = logging.getLogger("datalens.ai.router")

SENSITIVE_PATTERN = re.compile(
    r"(password|token|secret|key|credential|auth|cert|private)", re.IGNORECASE
)


class AIRoutingMode(StrEnum):
    GEMINI_ONLY = "GEMINI_ONLY"
    LOCAL_ONLY = "LOCAL_ONLY"
    HYBRID = "HYBRID"
    DETERMINISTIC_ONLY = "DETERMINISTIC_ONLY"


class AITaskType(StrEnum):
    QUESTION_INTERPRETATION = "QUESTION_INTERPRETATION"
    SCHEMA_EXPLANATION = "SCHEMA_EXPLANATION"
    ANALYTICAL_EXPLANATION = "ANALYTICAL_EXPLANATION"
    BUSINESS_REASONING = "BUSINESS_REASONING"
    REPORT_NARRATIVE = "REPORT_NARRATIVE"
    PROMPT_EVALUATION = "PROMPT_EVALUATION"
    SENSITIVE_DATA_ANALYSIS = "SENSITIVE_DATA_ANALYSIS"


class HybridAIRouter:
    """Centralized, privacy-aware AI provider router with dynamic fallback."""

    def __init__(
        self,
        routing_mode: str | None = None,
        gemini_provider: AIProvider | None = None,
        ollama_provider: AIProvider | None = None,
        fallback_provider: AIProvider | None = None,
    ) -> None:
        self.routing_mode = (routing_mode or settings.AI_ROUTING_MODE or "HYBRID").upper()

        # Instantiate providers
        effective_key = settings.effective_ai_api_key
        self.gemini: AIProvider | None = gemini_provider
        if not self.gemini and effective_key and settings.AI_ENABLED:
            try:
                self.gemini = GeminiProvider(
                    api_key=effective_key,
                    model=settings.effective_ai_model,
                    timeout_seconds=settings.AI_TIMEOUT_SECONDS,
                    max_retries=settings.AI_MAX_RETRIES,
                )
            except Exception as e:
                logger.warning(f"GeminiProvider init skipped: {e}")

        self.ollama: AIProvider = ollama_provider or OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
            temperature=settings.OLLAMA_TEMPERATURE,
        )

        self.fallback: AIProvider = fallback_provider or DeterministicAIProvider()

    # ---------------------------------------------------------------------------
    # Routing Decision Engine
    # ---------------------------------------------------------------------------

    async def select_provider(
        self,
        task_type: str = AITaskType.QUESTION_INTERPRETATION,
        dataset_sensitivity: str = "INTERNAL",
        cloud_permitted_by_policy: bool = True,
    ) -> tuple[AIProvider, str, str]:
        """Determine the active provider based on routing mode, task complexity, sensitivity, and availability.

        Returns (provider_instance, provider_name, reason).
        """
        # 1. Deterministic Mode forced or AI disabled
        if not settings.AI_ENABLED or self.routing_mode == AIRoutingMode.DETERMINISTIC_ONLY:
            return self.fallback, "deterministic", "Routing mode set to DETERMINISTIC_ONLY or AI disabled"

        # 2. Sensitivity constraint: CONFIDENTIAL or RESTRICTED strictly bars cloud AI
        is_sensitive = dataset_sensitivity.upper() in ("CONFIDENTIAL", "RESTRICTED")
        cloud_strictly_blocked = is_sensitive or (not cloud_permitted_by_policy)

        # 3. Mode LOCAL_ONLY or cloud blocked by policy
        if self.routing_mode == AIRoutingMode.LOCAL_ONLY or cloud_strictly_blocked:
            is_local_ok, local_err = await self.ollama.check_availability()
            if is_local_ok:
                reason = "Dataset sensitivity policy requires local processing" if cloud_strictly_blocked else "LOCAL_ONLY mode active"
                return self.ollama, "ollama", reason
            # If local offline and cloud blocked, fallback strictly to deterministic
            return self.fallback, "deterministic", f"Local Ollama unavailable ({local_err}) and cloud barred by policy"

        # 4. Mode GEMINI_ONLY
        if self.routing_mode == AIRoutingMode.GEMINI_ONLY:
            if self.gemini:
                is_gemini_ok, gemini_err = await self.gemini.check_availability()
                if is_gemini_ok:
                    return self.gemini, "gemini", "GEMINI_ONLY mode active"
            return self.fallback, "deterministic", "Gemini unavailable and mode is GEMINI_ONLY"

        # 5. Mode HYBRID: Task-based selection
        preferred_is_local = task_type in (
            AITaskType.QUESTION_INTERPRETATION,
            AITaskType.SCHEMA_EXPLANATION,
            AITaskType.ANALYTICAL_EXPLANATION,
            AITaskType.SENSITIVE_DATA_ANALYSIS,
        )

        if preferred_is_local:
            # Try Local (Ollama) first
            is_local_ok, _ = await self.ollama.check_availability()
            if is_local_ok:
                return self.ollama, "ollama", f"Hybrid task '{task_type}' routed to local AI"

            # Local offline -> Try Gemini fallback if permitted
            if self.gemini and not cloud_strictly_blocked:
                is_gemini_ok, _ = await self.gemini.check_availability()
                if is_gemini_ok:
                    return self.gemini, "gemini", "Local AI offline; fell back to Google Gemini"

            return self.fallback, "deterministic", "Local AI and Cloud AI unavailable; fell back to deterministic"

        else:
            # Preferred is Gemini (Business reasoning, Report narratives, Prompt Evaluation)
            if self.gemini and not cloud_strictly_blocked:
                is_gemini_ok, _ = await self.gemini.check_availability()
                if is_gemini_ok:
                    return self.gemini, "gemini", f"Hybrid task '{task_type}' routed to Google Gemini"

            # Gemini offline or unconfigured -> Try Local (Ollama)
            is_local_ok, _ = await self.ollama.check_availability()
            if is_local_ok:
                return self.ollama, "ollama", "Google Gemini unavailable; fell back to local Ollama"

            return self.fallback, "deterministic", "All AI providers unavailable; fell back to deterministic"

    # ---------------------------------------------------------------------------
    # Unified Public Execution Methods
    # ---------------------------------------------------------------------------

    async def generate_analysis_plan(
        self,
        question: str,
        schema_metadata: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
        dataset_sensitivity: str = "INTERNAL",
        cloud_permitted_by_policy: bool = True,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate structured analytical plan JSON via the routed provider."""
        start_time = time.time()
        provider, provider_name, reason = await self.select_provider(
            task_type=AITaskType.QUESTION_INTERPRETATION,
            dataset_sensitivity=dataset_sensitivity,
            cloud_permitted_by_policy=cloud_permitted_by_policy,
        )

        # Context minimization: clean schema metadata
        sanitized_schema = self._sanitize_metadata(schema_metadata)

        plan = await provider.generate_plan(question, sanitized_schema, conversation_history)
        telemetry = {
            "provider_used": provider_name,
            "routing_reason": reason,
            "latency_ms": int((time.time() - start_time) * 1000),
        }
        return plan, telemetry

    async def explain_results(
        self,
        question: str,
        plan: dict[str, Any],
        results_summary: dict[str, Any],
        evidence: dict[str, Any],
        dataset_sensitivity: str = "INTERNAL",
        cloud_permitted_by_policy: bool = True,
    ) -> tuple[str, dict[str, Any]]:
        """Generate grounded narrative explanation via the routed provider."""
        start_time = time.time()
        provider, provider_name, reason = await self.select_provider(
            task_type=AITaskType.ANALYTICAL_EXPLANATION,
            dataset_sensitivity=dataset_sensitivity,
            cloud_permitted_by_policy=cloud_permitted_by_policy,
        )

        explanation = await provider.generate_explanation(
            question, plan, results_summary, evidence
        )
        telemetry = {
            "provider_used": provider_name,
            "routing_reason": reason,
            "latency_ms": int((time.time() - start_time) * 1000),
        }
        return explanation, telemetry

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        task_type: str = AITaskType.BUSINESS_REASONING,
        dataset_sensitivity: str = "INTERNAL",
        cloud_permitted_by_policy: bool = True,
    ) -> dict[str, Any]:
        """Generate text via routed provider."""
        provider, provider_name, reason = await self.select_provider(
            task_type=task_type,
            dataset_sensitivity=dataset_sensitivity,
            cloud_permitted_by_policy=cloud_permitted_by_policy,
        )

        res = await provider.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        res["routing_reason"] = reason
        return res

    async def generate_structured_output(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        task_type: str = AITaskType.QUESTION_INTERPRETATION,
        dataset_sensitivity: str = "INTERNAL",
        cloud_permitted_by_policy: bool = True,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate structured JSON object via routed provider."""
        start_time = time.time()
        provider, provider_name, reason = await self.select_provider(
            task_type=task_type,
            dataset_sensitivity=dataset_sensitivity,
            cloud_permitted_by_policy=cloud_permitted_by_policy,
        )

        data = await provider.generate_structured(prompt, system_instruction, temperature)
        telemetry = {
            "provider_used": provider_name,
            "routing_reason": reason,
            "latency_ms": int((time.time() - start_time) * 1000),
        }
        return data, telemetry

    async def health_check_all(self) -> dict[str, Any]:
        """Perform comprehensive health check across all providers."""
        gemini_ok, gemini_err = (False, "Gemini not configured")
        if self.gemini:
            gemini_ok, gemini_err = await self.gemini.check_availability()

        ollama_ok, ollama_err = await self.ollama.check_availability()
        fallback_ok, _ = await self.fallback.check_availability()

        return {
            "active_routing_mode": self.routing_mode,
            "providers": {
                "gemini": {
                    "configured": bool(self.gemini),
                    "operational": gemini_ok,
                    "error": gemini_err,
                    "model": settings.effective_ai_model,
                },
                "ollama": {
                    "configured": True,
                    "operational": ollama_ok,
                    "error": ollama_err,
                    "model": settings.OLLAMA_MODEL,
                    "base_url": settings.OLLAMA_BASE_URL,
                },
                "deterministic": {
                    "configured": True,
                    "operational": fallback_ok,
                    "model": "heuristic-rules-v1",
                },
            },
        }

    # ---------------------------------------------------------------------------
    # Privacy & Context Minimization
    # ---------------------------------------------------------------------------

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        """Scrub secret credentials, tokens, and row values from metadata."""
        sanitized: dict[str, Any] = {}
        for k, v in metadata.items():
            if SENSITIVE_PATTERN.search(str(k)):
                sanitized[k] = "••••••••"
            elif isinstance(v, dict):
                sanitized[k] = HybridAIRouter._sanitize_metadata(v)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                sanitized[k] = [HybridAIRouter._sanitize_metadata(item) for item in v]
            else:
                sanitized[k] = v
        return sanitized

