import logging
from typing import Any

logger = logging.getLogger("datalens.analyst.opportunity")


class OpportunityEngine:
    """
    Measurable business opportunity discovery engine.
    Detects high-growth products, untapped high-margin segments,
    improving regions, and positive metric inflections.
    """

    @classmethod
    def evaluate_growth_opportunities(
        cls,
        breakdown_rows: list[dict[str, Any]],
        dimension_name: str,
        metric_name: str = "Revenue",
        value_key: str = "metric_value",
        growth_key: str = "growth_pct",
    ) -> list[dict[str, Any]]:
        """
        Discovers high-growth business segments and categories.
        """
        findings: list[dict[str, Any]] = []
        if not breakdown_rows:
            return findings

        # Filter for rows with measurable positive performance
        growth_candidates = []
        for r in breakdown_rows:
            growth = r.get(growth_key)
            val = r.get(value_key, 0)
            if growth is not None:
                try:
                    growth_val = float(growth)
                    if growth_val >= 15.0:  # 15%+ growth signal
                        growth_candidates.append({
                            "segment": str(r.get(dimension_name, "Segment")),
                            "growth_pct": growth_val,
                            "value": float(val or 0),
                        })
                except (ValueError, TypeError):
                    continue

        if not growth_candidates:
            # Fallback: if no growth_key in breakdown, look at top performing segment vs average
            vals = [float(r.get(value_key, 0) or 0) for r in breakdown_rows]
            if vals and sum(vals) > 0:
                avg_val = sum(vals) / len(vals)
                for r in breakdown_rows:
                    v = float(r.get(value_key, 0) or 0)
                    if v >= avg_val * 1.5:  # 50% above average
                        seg_name = str(r.get(dimension_name, "Segment"))
                        findings.append({
                            "title": f"High Performance Momentum in {seg_name}",
                            "category": "opportunity",
                            "severity": "HIGH",
                            "affected_metric": metric_name,
                            "affected_dimension": dimension_name,
                            "affected_segment": seg_name,
                            "summary": (
                                f"Segment '{seg_name}' generated {v:,.2f} in {metric_name}, outperforming "
                                f"the peer segment average ({avg_val:,.2f}) by {round(((v - avg_val)/avg_val)*100, 1)}%."
                            ),
                            "score": 0.80,
                            "priority_reason": "Observed segment performance is 50%+ above peer baseline.",
                            "recommended_action": f"Allocate additional commercial support and inventory to '{seg_name}' to sustain demand.",
                            "suggested_investigation": f"Evaluate customer acquisition channels and repeat order patterns for '{seg_name}'.",
                            "supporting_data": {"segment": seg_name, "value": v, "peer_average": avg_val},
                        })
                        break
            return findings

        # Sort by growth rate descending
        growth_candidates.sort(key=lambda x: x["growth_pct"], reverse=True)
        top_growth = growth_candidates[0]

        findings.append({
            "title": f"Accelerating Growth in {top_growth['segment']} (+{top_growth['growth_pct']}%)",
            "category": "opportunity",
            "severity": "HIGH",
            "affected_metric": metric_name,
            "affected_dimension": dimension_name,
            "affected_segment": top_growth["segment"],
            "summary": (
                f"Segment '{top_growth['segment']}' achieved {top_growth['growth_pct']:+.1f}% expansion, "
                f"reaching {top_growth['value']:,.2f} in observed {metric_name}."
            ),
            "score": round(min(0.95, 0.6 + (top_growth["growth_pct"] / 100.0)), 2),
            "priority_reason": f"Strong measurable expansion signal (+{top_growth['growth_pct']}%) exceeds industry growth threshold.",
            "recommended_action": f"Capitalize on positive momentum by expanding promotional campaigns in '{top_growth['segment']}'.",
            "suggested_investigation": f"Investigate channel adoption and market drivers behind '{top_growth['segment']}' expansion.",
            "supporting_data": {
                "segment": top_growth["segment"],
                "growth_pct": top_growth["growth_pct"],
                "value": top_growth["value"],
            },
        })

        return findings

    @classmethod
    def evaluate_margin_expansion_opportunity(
        cls,
        breakdown_rows: list[dict[str, Any]],
        dimension_name: str,
        revenue_key: str = "revenue",
        cost_key: str = "cost",
    ) -> list[dict[str, Any]]:
        """
        Identifies high-margin segments with volume expansion potential.
        """
        findings: list[dict[str, Any]] = []
        if not breakdown_rows:
            return findings

        high_margin_segs = []
        for r in breakdown_rows:
            rev = float(r.get(revenue_key, 0) or 0)
            cst = float(r.get(cost_key, 0) or 0)
            if rev > 0:
                profit = rev - cst
                margin_pct = round((profit / rev) * 100, 2)
                if margin_pct >= 40.0:  # 40%+ gross margin
                    high_margin_segs.append({
                        "segment": str(r.get(dimension_name, "Segment")),
                        "margin_pct": margin_pct,
                        "revenue": rev,
                        "profit": profit,
                    })

        if high_margin_segs:
            high_margin_segs.sort(key=lambda x: x["margin_pct"], reverse=True)
            top_margin = high_margin_segs[0]
            findings.append({
                "title": f"High Margin Expansion Signal: {top_margin['segment']} ({top_margin['margin_pct']}% Margin)",
                "category": "opportunity",
                "severity": "HIGH",
                "affected_metric": "Profit Margin",
                "affected_dimension": dimension_name,
                "affected_segment": top_margin["segment"],
                "summary": (
                    f"Segment '{top_margin['segment']}' exhibits a strong profit margin of {top_margin['margin_pct']}%, "
                    f"generating {top_margin['profit']:,.2f} profit on {top_margin['revenue']:,.2f} revenue."
                ),
                "score": 0.85,
                "priority_reason": f"High margin profile ({top_margin['margin_pct']}%) provides superior unit economics.",
                "recommended_action": f"Prioritize marketing acquisition spend towards '{top_margin['segment']}' to maximize blended margin.",
                "suggested_investigation": f"Evaluate customer acquisition costs for '{top_margin['segment']}' against customer lifetime value.",
                "supporting_data": top_margin,
            })

        return findings
