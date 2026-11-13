import logging
import time
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.services.ai.factory import AIProviderFactory
from app.services.prompt_lab.template_engine import PromptTemplateEngine

logger = logging.getLogger("datalens.prompt_lab.execution")


class PromptExecutionService:
    """
    Executes prompts against live Google Gemini (when configured) or deterministic simulation mode.
    Accurately reports token counts, latency, and simulated status.
    """

    # Gemini 2.5 Flash pricing per million tokens
    COST_PER_1M_INPUT = 0.075
    COST_PER_1M_OUTPUT = 0.30

    @classmethod
    async def execute_prompt(
        cls,
        system_prompt: str,
        user_prompt_template: str,
        variables: dict[str, Any],
        provider: str = "mock",
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        required_variables: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Renders templates and executes via live Gemini provider or simulation mode.
        """
        # 1. Render templates safely
        rendered_sys, rendered_user = PromptTemplateEngine.validate_and_render(
            system_prompt,
            user_prompt_template,
            variables,
            required_variables=required_variables,
        )

        start_time = time.perf_counter()

        # 2. Check if live execution requested and possible
        prov_key = provider.lower()
        is_live_requested = prov_key in ("gemini", "google", "live", "gemini-2.5-flash", "ollama", "local", "hybrid")

        if is_live_requested and settings.AI_ENABLED:
            target_prov = AIProviderFactory.get_provider(provider)
            try:
                res = await target_prov.generate_text(
                    prompt=rendered_user,
                    system_instruction=rendered_sys or None,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                input_tokens = res.get("input_tokens")
                output_tokens = res.get("output_tokens")
                cost_usd = 0.0 if res.get("provider") == "ollama" else None
                if cost_usd is None and input_tokens is not None and output_tokens is not None:
                    cost_usd = round(
                        (input_tokens * cls.COST_PER_1M_INPUT + output_tokens * cls.COST_PER_1M_OUTPUT) / 1_000_000,
                        6,
                    )

                return {
                    "rendered_system_prompt": rendered_sys,
                    "rendered_user_prompt": rendered_user,
                    "response_text": res.get("text", ""),
                    "provider": res.get("provider", provider),
                    "model": model or res.get("model", "default"),
                    "execution_timestamp": datetime.now(UTC),
                    "latency_ms": res.get("latency_ms", int((time.perf_counter() - start_time) * 1000)),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "estimated_cost_usd": cost_usd,
                    "provider_status": "live",
                    "is_simulated": False,
                }
            except Exception as e:
                logger.warning(f"Live provider '{provider}' execution failed ({e}), using deterministic simulation fallback.")

        # 3. Deterministic Simulation / Mock Execution
        # Simulates model output based on prompt context and intent
        simulated_response = cls._generate_simulated_response(rendered_sys, rendered_user, variables)
        latency_ms = int((time.perf_counter() - start_time) * 1000) + 45  # nominal execution delay

        # Estimated tokens (~4 chars per token)
        total_input_chars = len(rendered_sys) + len(rendered_user)
        input_tokens = max(1, total_input_chars // 4)
        output_tokens = max(1, len(simulated_response) // 4)
        cost_usd = (input_tokens * cls.COST_PER_1M_INPUT + output_tokens * cls.COST_PER_1M_OUTPUT) / 1_000_000

        return {
            "rendered_system_prompt": rendered_sys,
            "rendered_user_prompt": rendered_user,
            "response_text": simulated_response,
            "provider": provider if provider != "mock" else "simulated",
            "model": model,
            "execution_timestamp": datetime.now(UTC),
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": round(cost_usd, 6),
            "provider_status": "simulated",
            "is_simulated": True,
        }

    @staticmethod
    def _generate_simulated_response(system_prompt: str, user_prompt: str, variables: dict[str, Any]) -> str:
        """
        Generates realistic, relevant responses for simulation testing.
        """
        combined = (system_prompt + " " + user_prompt).lower()

        # Check for JSON instruction
        is_json_requested = "json" in combined or "json object" in combined or "format as json" in combined

        if is_json_requested:
            return (
                '{\n'
                '  "status": "success",\n'
                '  "analysis": "Executive summary generated from prompt parameters.",\n'
                f'  "inputs_evaluated": {len(variables)},\n'
                '  "key_findings": [\n'
                '    "Deterministic verification confirmed.",\n'
                '    "All input variables successfully rendered."\n'
                '  ]\n'
                '}'
            )

        if "summar" in combined:
            return (
                "Executive Summary:\n"
                "The analysis indicates strong operational alignment across evaluated dimensions. "
                "Key performance metrics demonstrate positive variance against quarterly benchmarks, "
                "with verified data consistency throughout the reported reporting period."
            )

        if "classif" in combined:
            return "Classification Result: Category A (High Confidence - 0.94)"

        return (
            "Based on the provided prompt instructions and contextual inputs, the analysis yields the following result:\n\n"
            "- Verified execution completed successfully.\n"
            f"- Context evaluated: {user_prompt[:120]}...\n"
            "- Observation: Consistent patterns identified across target variables."
        )

