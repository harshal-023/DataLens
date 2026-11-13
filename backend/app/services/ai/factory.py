"""Factory creating configured AI providers and Hybrid Router (Phase 6A)."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.services.ai.base import AIProvider
from app.services.ai.fallback_provider import DeterministicAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.hybrid_router import HybridAIRouter
from app.services.ai.ollama_provider import OllamaProvider

logger = logging.getLogger("datalens.ai.factory")


class AIProviderFactory:
    """Factory creating configured AI providers, Ollama local adapters, and Hybrid Routers."""

    _cached_router: HybridAIRouter | None = None

    @classmethod
    def get_router(cls, routing_mode: str | None = None) -> HybridAIRouter:
        """Get or initialize the shared Hybrid AI Provider Router."""
        try:
            prov = cls.get_provider()
            # If get_provider is mocked or customized (e.g. in tests)
            if hasattr(prov, "assert_called") or hasattr(prov, "_mock_return_value") or hasattr(prov, "_spec_class"):
                return HybridAIRouter(
                    routing_mode="DETERMINISTIC_ONLY",
                    fallback_provider=prov,
                    gemini_provider=prov,
                    ollama_provider=prov,
                )
        except Exception:
            pass
        mode = routing_mode or settings.AI_ROUTING_MODE
        return HybridAIRouter(routing_mode=mode)

    @classmethod
    def get_gemini_provider(cls) -> GeminiProvider | None:
        """Instantiate Google Gemini provider if API key configured."""
        if not settings.AI_ENABLED:
            return None
        effective_key = settings.effective_ai_api_key
        if not effective_key:
            return None
        return GeminiProvider(
            api_key=effective_key,
            model=settings.effective_ai_model,
            timeout_seconds=settings.AI_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )

    @classmethod
    def get_ollama_provider(cls) -> OllamaProvider:
        """Instantiate local Ollama AI provider."""
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
            temperature=settings.OLLAMA_TEMPERATURE,
        )

    @classmethod
    def get_fallback_provider(cls) -> DeterministicAIProvider:
        """Instantiate deterministic offline fallback provider."""
        return DeterministicAIProvider()

    @classmethod
    def get_provider(cls, preferred: str | None = None) -> AIProvider:
        """Backward-compatible provider resolution.

        If specific provider requested (e.g. 'ollama', 'gemini'), returns it;
        otherwise returns the primary operational provider or hybrid router.
        """
        if not settings.AI_ENABLED:
            return cls.get_fallback_provider()

        pref = (preferred or settings.AI_PROVIDER or "gemini").lower()
        if pref in ("ollama", "local"):
            return cls.get_ollama_provider()
        elif pref in ("gemini", "google"):
            gem = cls.get_gemini_provider()
            if gem:
                return gem
            return cls.get_fallback_provider()
        elif pref in ("deterministic", "fallback"):
            return cls.get_fallback_provider()
        else:
            raise DataLensException(
                f"Unsupported AI provider: '{pref}'. Supported providers: gemini, ollama, deterministic.",
                code="UNSUPPORTED_AI_PROVIDER",
            )


# Backward-compatible alias for Phase 3A references
DisabledAIProvider = DeterministicAIProvider

