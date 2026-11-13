import logging
from typing import Any

logger = logging.getLogger("datalens.analyst.trend")


class TrendEngine:
    """
    Deterministic trend discovery engine.
    Analyzes metrics over temporal dimensions to detect growth, decline,
    sustained movements, and growth rate changes while handling zero baselines safely.
    """

    @classmethod
    def evaluate_metric_trend(
        cls,
        time_series_rows: list[dict[str, Any]],
        metric_name: str,
        period_key: str = "period",
        value_key: str = "metric_value",
    ) -> list[dict[str, Any]]:
        """
        Takes chronologically ordered rows and evaluates trend findings.
        Returns a list of structured trend finding dictionaries.
        """
        findings: list[dict[str, Any]] = []
        if len(time_series_rows) < 2:
            return findings

        # Ensure values are float
        clean_pts: list[dict[str, Any]] = []
        for r in time_series_rows:
            period = str(r.get(period_key, ""))
            val = r.get(value_key)
            try:
                num_val = float(val) if val is not None else 0.0
                clean_pts.append({"period": period, "value": num_val})
            except (ValueError, TypeError):
                continue

        if len(clean_pts) < 2:
            return findings

        # 1. Latest Period-over-Period Delta
        prev_pt = clean_pts[-2]
        curr_pt = clean_pts[-1]
        abs_change = round(curr_pt["value"] - prev_pt["value"], 2)

        # Zero baseline handling
        pct_change: float | None = None
        pct_display: str
        if prev_pt["value"] == 0:
            if abs_change > 0:
                pct_display = "New activity from zero baseline"
            elif abs_change < 0:
                pct_display = "Negative from zero baseline"
            else:
                pct_display = "0.0% (Zero baseline unchanged)"
        else:
            pct_change = round((abs_change / abs(prev_pt["value"])) * 100, 2)
            pct_display = f"{pct_change:+.1f}%"

        # Check significance (e.g. > 5% movement)
        if pct_change is not None and abs(pct_change) >= 5.0:
            direction = "increase" if pct_change > 0 else "decline"
            severity = "HIGH" if abs(pct_change) >= 20.0 else "MEDIUM"
            findings.append({
                "type": "period_over_period",
                "title": f"Recent {direction.title()} in {metric_name} ({pct_display})",
                "summary": (
                    f"{metric_name} experienced a {pct_display} {direction} in period {curr_pt['period']} "
                    f"compared to {prev_pt['period']} (absolute change: {abs_change:+,.2f})."
                ),
                "metric_name": metric_name,
                "severity": severity,
                "baseline_value": f"{prev_pt['value']:,.2f}",
                "observed_value": f"{curr_pt['value']:,.2f}",
                "deviation_pct": pct_change,
                "direction": direction,
                "supporting_data": {
                    "periods": [prev_pt["period"], curr_pt["period"]],
                    "values": [prev_pt["value"], curr_pt["value"]],
                    "series_slice": clean_pts[-5:],
                },
            })

        # 2. Sustained Trend Detection (3+ consecutive directional changes)
        if len(clean_pts) >= 4:
            consecutive_growth = 0
            consecutive_decline = 0
            for i in range(1, len(clean_pts)):
                delta = clean_pts[i]["value"] - clean_pts[i - 1]["value"]
                if delta > 0:
                    consecutive_growth += 1
                    consecutive_decline = 0
                elif delta < 0:
                    consecutive_decline += 1
                    consecutive_growth = 0
                else:
                    consecutive_growth = 0
                    consecutive_decline = 0

            if consecutive_growth >= 3:
                start_pt = clean_pts[-consecutive_growth - 1]
                total_growth = round(curr_pt["value"] - start_pt["value"], 2)
                growth_pct = round((total_growth / abs(start_pt["value"])) * 100, 2) if start_pt["value"] != 0 else None
                findings.append({
                    "type": "sustained_trend",
                    "title": f"Sustained Growth in {metric_name} ({consecutive_growth} Periods)",
                    "summary": (
                        f"{metric_name} demonstrated consecutive period-over-period expansion across the last "
                        f"{consecutive_growth} intervals, totaling {total_growth:+,.2f} increase."
                    ),
                    "metric_name": metric_name,
                    "severity": "HIGH" if (growth_pct and growth_pct >= 25) else "MEDIUM",
                    "baseline_value": f"{start_pt['value']:,.2f}",
                    "observed_value": f"{curr_pt['value']:,.2f}",
                    "deviation_pct": growth_pct,
                    "direction": "sustained_growth",
                    "supporting_data": {"consecutive_periods": consecutive_growth, "series": clean_pts},
                })
            elif consecutive_decline >= 3:
                start_pt = clean_pts[-consecutive_decline - 1]
                total_decline = round(curr_pt["value"] - start_pt["value"], 2)
                decline_pct = round((total_decline / abs(start_pt["value"])) * 100, 2) if start_pt["value"] != 0 else None
                findings.append({
                    "type": "sustained_trend",
                    "title": f"Sustained Contraction in {metric_name} ({consecutive_decline} Periods)",
                    "summary": (
                        f"{metric_name} suffered continuous contraction across the last {consecutive_decline} intervals, "
                        f"dropping by {abs(total_decline):,.2f}."
                    ),
                    "metric_name": metric_name,
                    "severity": "CRITICAL" if (decline_pct and abs(decline_pct) >= 20) else "HIGH",
                    "baseline_value": f"{start_pt['value']:,.2f}",
                    "observed_value": f"{curr_pt['value']:,.2f}",
                    "deviation_pct": decline_pct,
                    "direction": "sustained_decline",
                    "supporting_data": {"consecutive_periods": consecutive_decline, "series": clean_pts},
                })

        return findings

