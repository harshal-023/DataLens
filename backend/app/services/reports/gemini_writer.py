import json
import logging
from typing import Any

from app.services.ai.factory import AIProviderFactory
from app.services.reports.deterministic_narrative import DeterministicNarrativeGenerator

logger = logging.getLogger("datalens.reports.gemini")


class GeminiReportWriter:
    """
    AI-powered business reporting narrative generator using Google Gemini API.
    Strictly grounds all explanations in verified evidence objects.
    Preserves raw-data privacy by transmitting only aggregated metrics.
    Automatically falls back to deterministic generation on any failure.
    """

    @classmethod
    async def generate_report_narratives(
        cls,
        report_title: str,
        report_type: str,
        kpis: list[dict[str, Any]],
        chart_data: list[dict[str, Any]] | None = None,
        top_performers: list[dict[str, Any]] | None = None,
        period: str | None = None,
    ) -> dict[str, Any]:
        """
        Returns a dict:
        {
          "executive_summary": str,
          "findings": list[str],
          "recommendations": list[str],
          "ai_generated": bool
        }
        """
        # 1. Obtain hybrid AI router
        router = AIProviderFactory.get_router()

        # 2. Build sanitized summary evidence payload (NO raw data rows)
        evidence_summary = {
            "report_title": report_title,
            "report_type": report_type,
            "period": period or "Current Reporting Window",
            "kpis": [
                {
                    "metric": k.get("metric"),
                    "value": k.get("value"),
                    "formatted": k.get("formatted_value"),
                    "comparison": k.get("comparison"),
                }
                for k in (kpis or [])
            ],
            "top_contributors": (top_performers or [])[:5],
            "sample_chart_aggregates": (chart_data or [])[:5],
        }

        prompt = f"""You are the Senior Executive Business Analyst for DataLens BI.
Write an executive narrative strictly based on the following verified numerical evidence.

RULES:
1. Do NOT invent or estimate any metrics. Cite ONLY the numbers provided in the evidence.
2. Clearly distinguish historical observed metrics from forward-looking recommendations.
3. Keep the tone professional, concise, objective, and executive-ready.
4. Respond in valid JSON with exactly the following schema:
{{
  "executive_summary": "2-3 paragraphs of polished executive overview and context.",
  "findings": ["3-5 distinct bullet point findings explaining key trends and variance."],
  "recommendations": ["3-4 actionable business recommendations grounded in the findings."]
}}

EVIDENCE PAYLOAD:
{json.dumps(evidence_summary, indent=2, default=str)}
"""

        try:
            raw_resp = await router.generate_text(
                prompt=prompt,
                system_instruction="You are DataLens Executive Business Reporter. Output valid JSON only.",
                temperature=0.2,
                max_tokens=1500,
                task_type="REPORT_NARRATIVE",
            )

            resp_text = raw_resp.get("text", "") if isinstance(raw_resp, dict) else str(raw_resp)

            # Parse JSON from response
            cleaned = resp_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            return {
                "executive_summary": parsed.get("executive_summary", ""),
                "findings": parsed.get("findings", []),
                "recommendations": parsed.get("recommendations", []),
                "ai_generated": True,
            }
        except Exception as e:
            logger.warning(f"Gemini narrative generation failed ({e}). Falling back to deterministic generator.")
            return cls._fallback(report_title, kpis, chart_data, top_performers, period)

    @classmethod
    def _fallback(
        cls,
        report_title: str,
        kpis: list[dict[str, Any]],
        chart_data: list[dict[str, Any]] | None,
        top_performers: list[dict[str, Any]] | None,
        period: str | None,
    ) -> dict[str, Any]:
        return {
            "executive_summary": DeterministicNarrativeGenerator.generate_executive_summary(
                report_title, kpis, top_performers, period
            ),
            "findings": DeterministicNarrativeGenerator.generate_findings(kpis, chart_data),
            "recommendations": DeterministicNarrativeGenerator.generate_recommendations(
                kpis, DeterministicNarrativeGenerator.generate_findings(kpis, chart_data)
            ),
            "ai_generated": False,
        }
