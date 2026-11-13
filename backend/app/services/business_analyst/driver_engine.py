import logging
from typing import Any

logger = logging.getLogger("datalens.analyst.driver")


class DriverEngine:
    """
    Deterministic driver and contribution decomposition engine.
    Calculates exact segment-level contribution deltas and reconciles individual
    contributions against the total aggregate change with neutral, rigorous business phrasing.
    """

    @classmethod
    def decompose_change_by_dimension(
        cls,
        current_breakdown: list[dict[str, Any]],
        previous_breakdown: list[dict[str, Any]],
        dimension_name: str,
        metric_name: str = "Revenue",
        value_key: str = "metric_value",
    ) -> dict[str, Any]:
        """
        Calculates segment contributions to aggregate metric change and verifies reconciliation.
        """
        curr_map = {str(r.get(dimension_name, "")): float(r.get(value_key, 0) or 0) for r in current_breakdown}
        prev_map = {str(r.get(dimension_name, "")): float(r.get(value_key, 0) or 0) for r in previous_breakdown}

        all_keys = set(curr_map.keys()).union(set(prev_map.keys()))

        total_curr = sum(curr_map.values())
        total_prev = sum(prev_map.values())
        total_delta = round(total_curr - total_prev, 2)
        total_pct_change = round((total_delta / total_prev) * 100, 2) if total_prev != 0 else None

        segment_deltas = []
        for key in all_keys:
            c_val = curr_map.get(key, 0.0)
            p_val = prev_map.get(key, 0.0)
            delta = round(c_val - p_val, 2)
            seg_pct = round((delta / p_val) * 100, 2) if p_val != 0 else None

            # Contribution share to overall delta
            contrib_share = round((delta / total_delta) * 100, 2) if total_delta != 0 else 0.0

            segment_deltas.append({
                "segment": key,
                "previous_value": p_val,
                "current_value": c_val,
                "delta": delta,
                "segment_pct_change": seg_pct,
                "contribution_to_total_delta_pct": contrib_share,
            })

        # Sort segments: if overall delta is negative, sort by most negative delta; if positive, most positive
        if total_delta < 0:
            segment_deltas.sort(key=lambda s: s["delta"])  # Most negative first
        else:
            segment_deltas.sort(key=lambda s: s["delta"], reverse=True)  # Most positive first

        # Mathematical Reconciliation Check
        sum_of_deltas = round(sum(s["delta"] for s in segment_deltas), 2)
        reconciled = abs(sum_of_deltas - total_delta) < 0.05

        # Format neutral observation narrative
        top_contributor = segment_deltas[0] if segment_deltas else None
        if total_delta < 0:
            direction_word = "decline"
            desc_text = (
                f"The overall {abs(total_delta):,.2f} {direction_word} ({total_pct_change:+.1f}%) "
                f"was concentrated in '{top_contributor['segment'] if top_contributor else 'key segments'}', "
                f"accounting for {top_contributor['contribution_to_total_delta_pct'] if top_contributor else 0.0}% of the net variance."
            )
        else:
            direction_word = "increase"
            desc_text = (
                f"The overall {total_delta:+,.2f} {direction_word} ({total_pct_change:+.1f}%) "
                f"was led by '{top_contributor['segment'] if top_contributor else 'key segments'}', "
                f"accounting for {top_contributor['contribution_to_total_delta_pct'] if top_contributor else 0.0}% of the net gain."
            )

        return {
            "dimension": dimension_name,
            "metric_name": metric_name,
            "total_previous": total_prev,
            "total_current": total_curr,
            "total_delta": total_delta,
            "total_pct_change": total_pct_change,
            "reconciled": reconciled,
            "reconciliation_variance": round(sum_of_deltas - total_delta, 4),
            "summary_statement": desc_text,
            "top_contributor": top_contributor,
            "segment_breakdowns": segment_deltas,
        }

