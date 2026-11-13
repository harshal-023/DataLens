import logging
from typing import Any

logger = logging.getLogger("datalens.analyst.risk")


class RiskEngine:
    """
    Rule-driven business risk detection engine.
    Detects revenue concentration, single-entity dependency, negative margins,
    rapid cost growth, and excessive volatility based on deterministic calculations.
    """

    # Configurable risk thresholds
    CUSTOMER_CONCENTRATION_HIGH = 25.0   # Single customer > 25% of revenue
    CUSTOMER_CONCENTRATION_MED = 15.0    # Single customer > 15% of revenue
    TOP_3_CONCENTRATION_HIGH = 50.0      # Top 3 customers > 50% of revenue
    
    PRODUCT_CONCENTRATION_HIGH = 40.0    # Single product > 40% of revenue
    REGIONAL_DEPENDENCE_HIGH = 60.0      # Single region > 60% of revenue

    @classmethod
    def evaluate_concentration_risk(
        cls,
        breakdown_rows: list[dict[str, Any]],
        dimension_name: str,
        metric_name: str = "Revenue",
        value_key: str = "metric_value",
    ) -> list[dict[str, Any]]:
        """
        Evaluates concentration across a categorical dimension (e.g., customer, product, region).
        """
        findings: list[dict[str, Any]] = []
        if not breakdown_rows:
            return findings

        # Sum total
        total_val = sum(float(r.get(value_key, 0) or 0) for r in breakdown_rows)
        if total_val <= 0:
            return findings

        # Sort descending by value
        sorted_rows = sorted(
            breakdown_rows,
            key=lambda r: float(r.get(value_key, 0) or 0),
            reverse=True,
        )

        top_entity = sorted_rows[0]
        top_name = str(top_entity.get(dimension_name, "Top Entity"))
        top_val = float(top_entity.get(value_key, 0) or 0)
        top_pct = round((top_val / total_val) * 100, 2)

        # 1. Single Entity Concentration Risk
        dim_lower = dimension_name.lower()
        if "customer" in dim_lower or "client" in dim_lower:
            if top_pct >= cls.CUSTOMER_CONCENTRATION_HIGH:
                findings.append({
                    "title": f"High Customer Concentration Risk ({top_name} at {top_pct}%)",
                    "category": "risk",
                    "severity": "CRITICAL" if top_pct >= 40.0 else "HIGH",
                    "affected_metric": metric_name,
                    "affected_dimension": dimension_name,
                    "affected_segment": top_name,
                    "summary": (
                        f"Customer '{top_name}' accounts for {top_pct}% ({top_val:,.2f}) of total {metric_name} "
                        f"({total_val:,.2f}), representing high account dependency."
                    ),
                    "score": round(min(1.0, top_pct / 50.0), 2),
                    "priority_reason": f"Top customer concentration of {top_pct}% exceeds enterprise risk threshold (25%).",
                    "recommended_action": "Develop diversification strategy and review key-account contract renewal timeline.",
                    "suggested_investigation": f"Analyze contract health and historical order stability for customer '{top_name}'.",
                    "supporting_data": {
                        "top_entity": top_name,
                        "entity_value": top_val,
                        "total_value": total_val,
                        "concentration_pct": top_pct,
                    },
                })
        elif "product" in dim_lower or "item" in dim_lower:
            if top_pct >= cls.PRODUCT_CONCENTRATION_HIGH:
                findings.append({
                    "title": f"Elevated Product Concentration Risk ({top_name} at {top_pct}%)",
                    "category": "risk",
                    "severity": "HIGH",
                    "affected_metric": metric_name,
                    "affected_dimension": dimension_name,
                    "affected_segment": top_name,
                    "summary": (
                        f"Product '{top_name}' generates {top_pct}% of total {metric_name}. "
                        "Supply chain disruptions or product life cycle decay poses outsized risk."
                    ),
                    "score": 0.75,
                    "priority_reason": f"Product concentration of {top_pct}% exceeds safe threshold (40%).",
                    "recommended_action": "Expand catalogue promotion to balance revenue generation across secondary products.",
                    "suggested_investigation": f"Inspect inventory availability and margin stability for '{top_name}'.",
                    "supporting_data": {"top_entity": top_name, "concentration_pct": top_pct},
                })
        elif "region" in dim_lower or "territory" in dim_lower:
            if top_pct >= cls.REGIONAL_DEPENDENCE_HIGH:
                findings.append({
                    "title": f"High Geographic Dependency Risk ({top_name} at {top_pct}%)",
                    "category": "risk",
                    "severity": "MEDIUM",
                    "affected_metric": metric_name,
                    "affected_dimension": dimension_name,
                    "affected_segment": top_name,
                    "summary": (
                        f"Geographic region '{top_name}' contributes {top_pct}% of overall business. "
                        "Business is vulnerable to local economic or regulatory headwinds."
                    ),
                    "score": 0.65,
                    "priority_reason": f"Single region accounts for {top_pct}% of business volume.",
                    "recommended_action": "Evaluate regional expansion opportunities in under-penetrated markets.",
                    "suggested_investigation": f"Compare customer acquisition costs in secondary regions against '{top_name}'.",
                    "supporting_data": {"top_entity": top_name, "concentration_pct": top_pct},
                })

        # 2. Top-3 Aggregate Concentration (e.g. for customers)
        if len(sorted_rows) >= 3 and ("customer" in dim_lower or "client" in dim_lower):
            top3_val = sum(float(r.get(value_key, 0) or 0) for r in sorted_rows[:3])
            top3_pct = round((top3_val / total_val) * 100, 2)
            if top3_pct >= cls.TOP_3_CONCENTRATION_HIGH and not findings:
                top3_names = ", ".join(str(r.get(dimension_name, "")) for r in sorted_rows[:3])
                findings.append({
                    "title": f"Top 3 Customer Concentration Risk ({top3_pct}%)",
                    "category": "risk",
                    "severity": "HIGH",
                    "affected_metric": metric_name,
                    "affected_dimension": dimension_name,
                    "affected_segment": top3_names,
                    "summary": f"The top 3 customers ({top3_names}) control {top3_pct}% of total business volume.",
                    "score": 0.70,
                    "priority_reason": f"Top 3 accounts represent {top3_pct}% of revenue (> 50% limit).",
                    "recommended_action": "Review multi-account retention programs and pipeline diversification.",
                    "suggested_investigation": "Audit customer churn risks across the top 3 accounts.",
                    "supporting_data": {"top3_pct": top3_pct, "top3_val": top3_val, "total_val": total_val},
                })

        return findings

    @classmethod
    def evaluate_margin_and_cost_risks(
        cls,
        revenue: float,
        cost: float,
        profit: float | None = None,
        prev_revenue: float | None = None,
        prev_cost: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Evaluates negative profit margin and rapid cost inflation outstripping top-line revenue.
        """
        findings: list[dict[str, Any]] = []

        # 1. Negative Profit Margin Check
        calculated_profit = profit if profit is not None else (revenue - cost)
        if revenue > 0:
            margin_pct = round((calculated_profit / revenue) * 100, 2)
            if margin_pct < 0:
                findings.append({
                    "title": f"Negative Profit Margin Detected ({margin_pct}%)",
                    "category": "risk",
                    "severity": "CRITICAL" if margin_pct <= -10.0 else "HIGH",
                    "affected_metric": "Profit Margin",
                    "affected_dimension": "Profitability",
                    "affected_segment": "Overall",
                    "summary": (
                        f"Current operating profit is negative ({calculated_profit:,.2f}), "
                        f"yielding a profit margin of {margin_pct}%."
                    ),
                    "score": 0.90,
                    "priority_reason": "Negative profit margin threatens operational viability.",
                    "recommended_action": "Immediate cost structure audit and price elasticity review.",
                    "suggested_investigation": "Drill into unit COGS and variable cost drivers to isolate loss sources.",
                    "supporting_data": {
                        "revenue": revenue,
                        "cost": cost,
                        "profit": calculated_profit,
                        "margin_pct": margin_pct,
                    },
                })

        # 2. Cost Inflation Outstripping Revenue
        if prev_revenue is not None and prev_cost is not None and prev_revenue > 0 and prev_cost > 0:
            rev_growth = round(((revenue - prev_revenue) / prev_revenue) * 100, 2)
            cost_growth = round(((cost - prev_cost) / prev_cost) * 100, 2)

            if cost_growth >= rev_growth + 10.0 and cost_growth > 5.0:
                findings.append({
                    "title": f"Cost Growth Outpacing Revenue (Cost: {cost_growth:+,.1f}% vs Rev: {rev_growth:+,.1f}%)",
                    "category": "risk",
                    "severity": "HIGH",
                    "affected_metric": "Cost Growth",
                    "affected_dimension": "Operating Costs",
                    "affected_segment": "Cost Structure",
                    "summary": (
                        f"Operating costs increased by {cost_growth:+.1f}%, outpacing top-line revenue growth "
                        f"of {rev_growth:+.1f}% by {round(cost_growth - rev_growth, 1)} percentage points."
                    ),
                    "score": 0.80,
                    "priority_reason": "Asymmetric cost growth compresses gross margins.",
                    "recommended_action": "Review supplier agreements and variable overhead commitments.",
                    "suggested_investigation": "Decompose cost variance by supplier and category.",
                    "supporting_data": {
                        "rev_growth": rev_growth,
                        "cost_growth": cost_growth,
                        "spread": round(cost_growth - rev_growth, 1),
                    },
                })

        return findings

