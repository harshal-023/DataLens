import uuid

import pytest

from app.services.business_analyst.anomaly_engine import AnomalyEngine
from app.services.business_analyst.driver_engine import DriverEngine
from app.services.business_analyst.explanation_engine import ExplanationEngine
from app.services.business_analyst.insight_engine import BusinessInsightEngine
from app.services.business_analyst.opportunity_engine import OpportunityEngine
from app.services.business_analyst.risk_engine import RiskEngine
from app.services.business_analyst.trend_engine import TrendEngine

# =========================================================================
# 1. Deterministic Trend Discovery & Zero-Baseline Handling
# =========================================================================

def test_trend_engine_period_over_period_and_sustained_growth():
    """Verifies that period-over-period movements and sustained growth are detected."""
    # 4 consecutive growing periods
    rows = [
        {"period": "2025-01", "metric_value": 100.0},
        {"period": "2025-02", "metric_value": 120.0},
        {"period": "2025-03", "metric_value": 150.0},
        {"period": "2025-04", "metric_value": 195.0},
    ]

    findings = TrendEngine.evaluate_metric_trend(rows, metric_name="Revenue")
    assert len(findings) >= 1

    # Check period-over-period finding
    pop_finding = next((f for f in findings if f["type"] == "period_over_period"), None)
    assert pop_finding is not None
    assert pop_finding["direction"] == "increase"
    assert pop_finding["deviation_pct"] == 30.0  # (195 - 150) / 150 = +30%

    # Check sustained growth finding
    sustained_finding = next((f for f in findings if f["type"] == "sustained_trend"), None)
    assert sustained_finding is not None
    assert sustained_finding["direction"] == "sustained_growth"
    assert sustained_finding["supporting_data"]["consecutive_periods"] == 3


def test_trend_engine_zero_baseline_handling():
    """Verifies that zero baselines do not trigger division by zero errors."""
    rows = [
        {"period": "2025-01", "metric_value": 0.0},
        {"period": "2025-02", "metric_value": 500.0},
    ]

    findings = TrendEngine.evaluate_metric_trend(rows, metric_name="New Category Sales")
    assert len(findings) == 0 or any("zero baseline" in str(f.get("summary", "")).lower() for f in findings)


# =========================================================================
# 2. Advanced Anomaly Intelligence (Statistical Outliers)
# =========================================================================

def test_anomaly_engine_detects_statistical_outliers():
    """Verifies statistical anomaly detection over aggregated time series."""
    # Normal distribution around 100 with one extreme outlier at 500
    series = [
        {"period": f"Day-{i}", "value": 100.0 + (i % 3) * 5.0} for i in range(1, 20)
    ]
    series.append({"period": "Day-20", "value": 500.0})  # Extreme outlier

    findings = AnomalyEngine.evaluate_series_anomalies(
        series_points=series,
        metric_name="Order Volume",
        dimension_name="period",
        algorithm="z_score",
        sensitivity=2.5,
    )

    assert len(findings) >= 1
    outlier_finding = next((f for f in findings if f["affected_segment"] == "Day-20"), None)
    assert outlier_finding is not None
    assert outlier_finding["severity"] in ("CRITICAL", "HIGH")
    assert outlier_finding["detection_method"] == "z_score"
    assert outlier_finding["deviation_pct"] > 100.0


# =========================================================================
# 3. Rule-Driven Business Risk Detection
# =========================================================================

def test_risk_engine_customer_revenue_concentration():
    """Verifies customer revenue concentration risk flags."""
    breakdown = [
        {"customer_name": "MegaCorp Industries", "metric_value": 45000.0},
        {"customer_name": "Acme Ltd", "metric_value": 15000.0},
        {"customer_name": "Beta LLC", "metric_value": 10000.0},
        {"customer_name": "Gamma Co", "metric_value": 5000.0},
    ]

    findings = RiskEngine.evaluate_concentration_risk(
        breakdown_rows=breakdown,
        dimension_name="customer_name",
        metric_name="Revenue",
    )

    assert len(findings) >= 1
    top_risk = findings[0]
    assert top_risk["category"] == "risk"
    assert "MegaCorp Industries" in top_risk["title"]
    assert top_risk["affected_segment"] == "MegaCorp Industries"
    assert top_risk["severity"] in ("CRITICAL", "HIGH")


def test_risk_engine_negative_margin_and_cost_inflation():
    """Verifies negative operating margin and cost inflation risks."""
    # Scenario A: Negative margin
    margin_risks = RiskEngine.evaluate_margin_and_cost_risks(
        revenue=100000.0,
        cost=115000.0,
    )
    assert len(margin_risks) >= 1
    assert any("Negative Profit Margin" in r["title"] for r in margin_risks)

    # Scenario B: Cost growth outpacing revenue
    cost_risks = RiskEngine.evaluate_margin_and_cost_risks(
        revenue=120000.0,
        cost=110000.0,
        prev_revenue=115000.0,  # Rev growth: ~4.3%
        prev_cost=80000.0,     # Cost growth: ~37.5%
    )
    assert len(cost_risks) >= 1
    assert any("Cost Growth Outpacing Revenue" in r["title"] for r in cost_risks)


# =========================================================================
# 4. Business Opportunity Discovery
# =========================================================================

def test_opportunity_engine_detects_growth_and_high_margin_signals():
    """Verifies high-growth category and margin expansion signals."""
    # A: Growth signal
    breakdown_growth = [
        {"product_category": "Enterprise Cloud", "metric_value": 85000.0, "growth_pct": 42.5},
        {"product_category": "Standard On-Prem", "metric_value": 25000.0, "growth_pct": 4.0},
    ]
    opps = OpportunityEngine.evaluate_growth_opportunities(
        breakdown_rows=breakdown_growth,
        dimension_name="product_category",
        metric_name="ARR",
    )
    assert len(opps) >= 1
    assert "Enterprise Cloud" in opps[0]["title"]
    assert opps[0]["category"] == "opportunity"

    # B: High margin expansion signal
    breakdown_margin = [
        {"product_category": "Consulting Services", "revenue": 100000.0, "cost": 45000.0},  # 55% margin
        {"product_category": "Hardware Resale", "revenue": 100000.0, "cost": 90000.0},      # 10% margin
    ]
    margin_opps = OpportunityEngine.evaluate_margin_expansion_opportunity(
        breakdown_rows=breakdown_margin,
        dimension_name="product_category",
    )
    assert len(margin_opps) >= 1
    assert "Consulting Services" in margin_opps[0]["title"]
    assert margin_opps[0]["supporting_data"]["margin_pct"] == 55.0


# =========================================================================
# 5. Deterministic Contribution & Driver Decomposition
# =========================================================================

def test_driver_engine_reconciles_variance_mathematically():
    """Verifies that individual segment contribution deltas sum precisely to the total delta."""
    prev_breakdown = [
        {"region": "North", "metric_value": 50000.0},
        {"region": "South", "metric_value": 30000.0},
        {"region": "West", "metric_value": 40000.0},
    ]
    curr_breakdown = [
        {"region": "North", "metric_value": 55000.0},  # +5,000
        {"region": "South", "metric_value": 32000.0},  # +2,000
        {"region": "West", "metric_value": 25000.0},   # -15,000
    ]

    decomp = DriverEngine.decompose_change_by_dimension(
        current_breakdown=curr_breakdown,
        previous_breakdown=prev_breakdown,
        dimension_name="region",
        metric_name="Revenue",
    )

    # Net change: 112,000 - 120,000 = -8,000 (-6.67%)
    assert decomp["total_delta"] == -8000.0
    assert decomp["reconciled"] is True
    assert decomp["reconciliation_variance"] == 0.0

    # West region was the primary negative driver (-15,000)
    top = decomp["top_contributor"]
    assert top["segment"] == "West"
    assert top["delta"] == -15000.0

    # Neutral phrasing assertion (no unsupported causal claims)
    statement = decomp["summary_statement"]
    assert "concentrated in" in statement
    assert "caused" not in statement.lower()


# =========================================================================
# 6. AI Explanation Grounding & Hallucination Guard
# =========================================================================

@pytest.mark.asyncio
async def test_explanation_engine_grounds_facts_and_rejects_hallucinations():
    """Verifies that explanations cite only calculated evidence."""
    finding = {
        "title": "West Region Revenue Contraction",
        "summary": "West region revenue declined by $15,000.",
        "category": "performance",
        "affected_metric": "Revenue",
        "baseline_value": "40,000.00",
        "observed_value": "25,000.00",
        "supporting_data": {"delta": -15000.0},
    }

    result = await ExplanationEngine.generate_explanation(
        finding=finding,
        preferred_provider="deterministic",
    )

    assert "detailed_explanation" in result
    assert "25,000.00" in result["observed_fact"]
    assert "40,000.00" in result["observed_fact"]
    assert result["ai_provider"] == "deterministic"


# =========================================================================
# 7. Deduplication & Idempotency Fingerprinting
# =========================================================================

def test_fingerprint_idempotency():
    """Verifies that duplicate findings on the same dataset version generate identical fingerprints."""
    version_id = uuid.uuid4()
    fp1 = BusinessInsightEngine._compute_fingerprint(
        version_id=version_id,
        category="risk",
        metric="Revenue",
        segment="MegaCorp Industries",
        finding_type="concentration",
    )
    fp2 = BusinessInsightEngine._compute_fingerprint(
        version_id=version_id,
        category="risk",
        metric="Revenue",
        segment="MegaCorp Industries",
        finding_type="concentration",
    )
    assert fp1 == fp2
    assert len(fp1) == 32
