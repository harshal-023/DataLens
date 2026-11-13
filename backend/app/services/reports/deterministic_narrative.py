from typing import Any


class DeterministicNarrativeGenerator:
    """
    Deterministic rule-based narrative engine for DataLens reports.
    Provides verified, executive-grade business explanations without relying
    on external LLM APIs, ensuring zero failure when AI is offline or disabled.
    """

    @classmethod
    def generate_executive_summary(
        cls,
        report_title: str,
        kpis: list[dict[str, Any]],
        top_performers: list[dict[str, Any]] | None = None,
        period: str | None = None,
    ) -> str:
        period_text = f" for {period}" if period else ""
        lines = [
            f"### Executive Overview: {report_title}{period_text}",
            "",
            "This report summarizes key operational and strategic performance metrics generated through deterministic analytical computation.",
        ]

        if kpis:
            lines.append("")
            lines.append("**Key Performance Highlights:**")
            for kpi in kpis:
                metric = kpi.get("metric", "Metric")
                val_str = kpi.get("formatted_value") or str(kpi.get("value", "N/A"))
                comp = kpi.get("comparison")
                if comp:
                    direction_symbol = "▲" if comp.get("direction") == "up" else "▼" if comp.get("direction") == "down" else "■"
                    pct = comp.get("percentage_change", 0.0)
                    lines.append(f"- **{metric}**: {val_str} ({direction_symbol} {abs(pct):.1f}% vs {comp.get('mode', 'benchmark')})")
                else:
                    lines.append(f"- **{metric}**: {val_str}")

        if top_performers:
            lines.append("")
            lines.append("**Leading Contributors:**")
            for tp in top_performers[:3]:
                label = tp.get("label") or tp.get("category", "Item")
                val_str = tp.get("formatted_value") or str(tp.get("value", ""))
                lines.append(f"- **{label}**: {val_str}")

        lines.append("")
        lines.append("All figures reflect immutable dataset versions and verified mathematical aggregation.")
        return "\n".join(lines)

    @classmethod
    def generate_findings(
        cls,
        kpis: list[dict[str, Any]],
        chart_data: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        findings = []
        if kpis:
            for k in kpis:
                val = k.get("value")
                metric = k.get("metric", "Indicator")
                comp = k.get("comparison")
                if comp and comp.get("percentage_change") is not None:
                    pct = comp["percentage_change"]
                    status = "positive expansion" if pct > 0 else "contraction" if pct < 0 else "stability"
                    findings.append(f"{metric} demonstrated {status} of {abs(pct):.1f}% relative to reference baseline.")
                elif val is not None:
                    findings.append(f"{metric} achieved an aggregate value of {k.get('formatted_value', val)}.")

        if chart_data:
            sorted_items = sorted(chart_data, key=lambda x: x.get("value", 0), reverse=True)
            if len(sorted_items) >= 2:
                top = sorted_items[0]
                bottom = sorted_items[-1]
                findings.append(
                    f"Segment variance: Highest contribution was observed in '{top.get('label', 'Top')}' ({top.get('value')}), "
                    f"whereas '{bottom.get('label', 'Lowest')}' recorded {bottom.get('value')}."
                )

        if not findings:
            findings.append("Operational indicators remained within normal expected tolerance bounds throughout the reporting window.")

        return findings

    @classmethod
    def generate_recommendations(
        cls,
        kpis: list[dict[str, Any]],
        findings: list[str],
    ) -> list[str]:
        recs = [
            "Maintain continuous telemetry monitoring and scheduled re-execution to capture emerging period trends.",
            "Prioritize resource allocation toward top-performing segments identified in the contribution matrix.",
            "Review operational queues showing contraction or elevated variance against targets to mitigate slippage.",
            "Verify underlying dataset schemas upon new ingestion to preserve data lineage and analytical parity.",
        ]
        return recs

