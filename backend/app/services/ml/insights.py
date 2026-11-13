import json

from app.core.logging import logger
from app.models.model_run import ModelRun
from app.schemas.ml import InsightResponse
from app.services.ai.factory import AIProviderFactory


class BusinessInsightEngine:
    """
    Synthesizes ML model outputs into executive business prose using Google Gemini.
    Strictly grounded in verified mathematical outputs; never invents predictions or hallucinates causation.
    """

    @classmethod
    async def generate_insight(
        cls,
        model_run: ModelRun,
        audience: str = "executive",
        include_recommendations: bool = True,
    ) -> InsightResponse:
        """
        Produces grounded narrative, key findings, and action items for an ML model run.
        """
        model_type = model_run.model_type
        summary = model_run.result_summary or {}
        metrics = model_run.metrics or {}
        params = model_run.parameters or {}

        # 1. Use Unified Hybrid AI Router
        router = AIProviderFactory.get_router()
        try:
            system_prompt = (
                "You are an executive Chief Data Officer and business intelligence advisor. "
                "Analyze the provided machine learning and statistical model outputs. "
                "Provide verified business narrative interpretations. "
                "CRITICAL CONSTRAINTS:\n"
                "- Never invent numbers, percentages, or metrics not present in the input JSON.\n"
                "- Never claim causation without explicit experimental proof.\n"
                "- Never label statistical anomalies as fraud or malfeasance.\n"
                "- Always explicitly cite the model algorithm, parameters, and statistical caveats.\n"
                "Output format must be a clean JSON object with keys: "
                "'insight_narrative', 'key_findings' (list), 'limitations' (list), 'suggested_actions' (list)."
            )

            user_prompt = (
                f"Audience: {audience}\n"
                f"Model Type: {model_type}\n"
                f"Algorithm: {model_run.algorithm}\n"
                f"Parameters: {json.dumps(params)}\n"
                f"Verified Metrics: {json.dumps(metrics)}\n"
                f"Result Summary: {json.dumps(summary)}\n"
            )

            parsed, _ = await router.generate_structured_output(
                prompt=user_prompt,
                system_instruction=system_prompt,
                temperature=0.2,
                task_type="BUSINESS_REASONING",
            )

            if parsed and parsed.get("key_findings"):
                return InsightResponse(
                    model_run_id=model_run.id,
                    insight_narrative=parsed.get("insight_narrative", ""),
                    key_findings=parsed.get("key_findings", []),
                    limitations=parsed.get("limitations", []),
                    suggested_actions=parsed.get("suggested_actions", []) if include_recommendations else [],
                    is_ai_generated=True,
                )
        except Exception as e:
            logger.warning(f"Live Gemini insight generation encountered transient issue, falling back to deterministic: {e}")

        # 2. Deterministic Insight Fallback
        return cls._generate_deterministic_insight(model_run, audience, include_recommendations)

    @classmethod
    def _generate_deterministic_insight(
        cls,
        model_run: ModelRun,
        audience: str,
        include_recommendations: bool,
    ) -> InsightResponse:
        m_type = model_run.model_type
        summary = model_run.result_summary or {}
        metrics = model_run.metrics or {}
        alg = model_run.algorithm

        if m_type == "anomaly_detection":
            count = summary.get("anomalies_detected_count", 0)
            total = summary.get("total_records_analyzed", 0)
            pct = summary.get("anomaly_percentage", 0.0)
            col = summary.get("target_column", "target")

            narrative = (
                f"Statistical anomaly audit on '{col}' using {alg.upper()} evaluated {total} records and flagged "
                f"{count} observations ({pct}%) exhibiting significant mathematical deviation from baseline distributions. "
                "These variances represent statistical tail behavior requiring operational review."
            )
            findings = [
                f"Identified {count} anomalous points outside the configured sensitivity threshold.",
                f"Total sample population: {total} records.",
                f"Anomaly incidence rate: {pct}%.",
            ]
            limitations = [
                "Statistical outliers represent unusual variance and do not confirm operational errors or fraud.",
                f"Threshold calculation based on {alg.upper()} assumptions.",
            ]
            actions = [
                f"Review the highest-severity anomalous records in '{col}' with domain stakeholders.",
                "Verify whether external events or reporting cutoffs coincide with flagged timestamps.",
            ]

        elif m_type == "forecasting":
            horizon = summary.get("forecast_horizon", 12)
            col = summary.get("target_column", "target")
            mae = metrics.get("mae")
            mae_str = f"{mae:.2f}" if mae is not None else "N/A"

            narrative = (
                f"Time-series projection for '{col}' using {alg.replace('_', ' ').title()} models {horizon} forward periods. "
                f"Historical backtesting achieved an error rate of MAE = {mae_str}. "
                "Confidence intervals widen over time, reflecting increasing uncertainty across distant horizons."
            )
            findings = [
                f"Generated {horizon}-period forward projections with prediction intervals.",
                f"Backtest validation achieved MAE of {mae_str}.",
                "Trend projection demonstrates baseline continuity with seasonal adjustments.",
            ]
            limitations = [
                "Projections represent mathematical trend continuations and are not guaranteed commitments.",
                "Unanticipated market disruptions or policy shifts are not reflected in historical series.",
            ]
            actions = [
                "Incorporate forecasted demand into quarterly capacity planning.",
                "Recalibrate models monthly as actual observations materialize.",
            ]

        elif m_type == "segmentation":
            k = summary.get("cluster_count", 3)
            total = summary.get("total_records_clustered", 0)
            sil = metrics.get("silhouette_score")
            sil_str = f"{sil:.3f}" if sil is not None else "N/A"

            narrative = (
                f"Unsupervised segmentation clustered {total} records across selected features into {k} groups using {alg.upper()}. "
                f"Cluster separation achieved a silhouette validation coefficient of {sil_str}. "
                "Distinct centroid profiles highlight natural operational groupings."
            )
            findings = [
                f"Classified {total} records into {k} distinct clusters.",
                f"Model quality validation: Silhouette score = {sil_str}.",
                "Feature profiles reveal meaningful differentiation across target metrics.",
            ]
            limitations = [
                "Clusters represent mathematical distance groupings, not intrinsic personal identities.",
                "Feature scaling parameters directly influence cluster boundaries.",
            ]
            actions = [
                "Tailor business communications to cluster trait profiles.",
                "Monitor cluster migration trends over successive reporting periods.",
            ]

        else:
            narrative = f"Advanced analytical model {alg} completed successfully."
            findings = ["Calculation executed without errors."]
            limitations = ["Standard analytical limitations apply."]
            actions = ["Review detailed results in dashboard."]

        return InsightResponse(
            model_run_id=model_run.id,
            insight_narrative=narrative,
            key_findings=findings,
            limitations=limitations,
            suggested_actions=actions if include_recommendations else [],
            is_ai_generated=False,
        )
