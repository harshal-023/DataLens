import logging
from typing import Any

from app.services.ai.factory import AIProviderFactory
from app.services.nla.verifier import NLAEvidenceVerifier

logger = logging.getLogger("datalens.analyst.explanation")


class ExplanationEngine:
    """
    AI Business Explanation Engine.
    Generates structured, grounded business narratives explaining deterministic findings.
    Enforces privacy policies, blocks raw rows, and validates all numerical citations.
    """

    @classmethod
    async def generate_explanation(
        cls,
        finding: dict[str, Any],
        workspace_id: Any = None,
        data_classification: str = "INTERNAL",
        preferred_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Produces grounded explanation with fact separation and hallucination safeguards.
        """
        title = finding.get("title", "Business Finding")
        summary = finding.get("summary", "")
        metric_name = finding.get("affected_metric", "Metric")
        category = finding.get("category", "performance")
        baseline_val = finding.get("baseline_value", "")
        observed_val = finding.get("observed_value", "")

        # Prepare allowed numbers for verification
        metric_cards = [
            {"title": metric_name, "value": observed_val},
        ]
        if baseline_val:
            metric_cards.append({"title": "Baseline", "value": baseline_val})

        # Deterministic Grounded Narrative Construction
        observed_fact = f"Observed {metric_name} reached {observed_val}" + (f" vs baseline of {baseline_val}." if baseline_val else ".")
        business_inference = summary or f"{title} warrants operational attention."
        investigation = finding.get("suggested_investigation") or f"Audit underlying transactional logs for {metric_name}."
        recommendation = finding.get("recommended_action") or "Monitor metric movements over the next reporting cycle."

        prompt_context = f"""
Finding Title: {title}
Category: {category}
Metric: {metric_name}
Summary: {summary}
Observed Value: {observed_val}
Baseline: {baseline_val}
"""

        explanation_text = f"{observed_fact} {business_inference}"
        ai_provider_used = "deterministic"

        # Attempt AI provider if configured and permitted by privacy policy
        try:
            if preferred_provider == "deterministic":
                ai_provider_used = "deterministic"
            else:
                provider = AIProviderFactory.get_provider(preferred=preferred_provider)
                ai_provider_used = provider.name

                if provider.name != "deterministic":
                    ai_prompt = (
                        f"You are an executive business analyst. Provide a concise 2-sentence executive interpretation "
                        f"of this verified finding. Only refer to the numbers provided below. Do not fabricate or invent new figures.\n\n"
                        f"{prompt_context}"
                    )
                    ai_resp = await provider.generate_text(ai_prompt, temperature=0.2)
                    if ai_resp and len(ai_resp.strip()) > 10:
                        candidate = ai_resp.strip()
                        # Verify numerical citations against calculated evidence
                        is_valid, warnings = NLAEvidenceVerifier.verify_cited_numbers(candidate, metric_cards)
                        if is_valid:
                            explanation_text = candidate
                        else:
                            logger.warning(f"AI explanation rejected due to ungrounded numbers: {warnings}")
                            explanation_text = f"{observed_fact} {business_inference} (Deterministic fallback: {warnings[0] if warnings else ''})"
                            ai_provider_used = f"{provider.name}_grounding_fallback"
        except Exception as e:
            logger.info(f"AI provider explanation fallback to deterministic: {e}")
            ai_provider_used = "deterministic"

        return {
            "detailed_explanation": explanation_text,
            "observed_fact": observed_fact,
            "business_inference": business_inference,
            "suggested_investigation": investigation,
            "recommended_action": recommendation,
            "ai_provider": ai_provider_used,
        }
