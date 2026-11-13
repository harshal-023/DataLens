import logging
from typing import Any

from app.services.ml.anomaly import AnomalyDetectionService

logger = logging.getLogger("datalens.analyst.anomaly")


class AnomalyEngine:
    """
    Automated anomaly discovery engine.
    Wraps Phase 3C AnomalyDetectionService to discover outliers and statistical anomalies
    in business series, strictly distinguishing statistical variance from operational faults.
    """

    @classmethod
    def evaluate_series_anomalies(
        cls,
        series_points: list[dict[str, Any]],
        metric_name: str,
        dimension_name: str = "period",
        algorithm: str = "z_score",
        sensitivity: float = 2.5,
    ) -> list[dict[str, Any]]:
        """
        Executes statistical anomaly detection over numerical data series.
        Returns a list of structured anomaly finding dictionaries.
        """
        findings: list[dict[str, Any]] = []
        if len(series_points) < 5:
            return findings

        # Map series to standard format expected by AnomalyDetectionService: list of {"period": ..., "value": ...}
        prepared_pts: list[dict[str, Any]] = []
        for i, pt in enumerate(series_points):
            label = str(pt.get(dimension_name, pt.get("period", f"Point-{i}")))
            val = pt.get("value", pt.get("metric_value", pt.get(metric_name)))
            try:
                if val is not None:
                    prepared_pts.append({
                        "period": label,
                        "value": float(val),
                        "row_id": i,
                    })
            except (ValueError, TypeError):
                continue

        if len(prepared_pts) < 5:
            return findings

        try:
            res = AnomalyDetectionService.detect_anomalies(
                series_data=prepared_pts,
                target_column="value",
                algorithm=algorithm,
                sensitivity=sensitivity,
            )

            # Process discovered anomalous points
            for pt in res.anomalous_points:
                val_num = pt.actual_value
                base_num = pt.expected_value if pt.expected_value is not None else 0.0
                period_str = pt.timestamp or (prepared_pts[pt.row_index]["period"] if pt.row_index < len(prepared_pts) else f"Row-{pt.row_index}")
                dev_pct = round(((val_num - base_num) / abs(base_num)) * 100, 2) if base_num != 0 else 100.0

                sev = pt.severity.upper() if pt.severity else "MEDIUM"
                if abs(dev_pct) >= 100.0 or pt.anomaly_score >= 4.0:
                    severity = "CRITICAL"
                elif sev == "HIGH" or abs(dev_pct) >= 50.0:
                    severity = "HIGH"
                else:
                    severity = "MEDIUM"

                findings.append({
                    "type": "statistical_anomaly",
                    "title": f"Statistical Anomaly in {metric_name} ({period_str})",
                    "summary": (
                        f"Observed value of {val_num:,.2f} at '{period_str}' deviates by {dev_pct:+.1f}% "
                        f"from the statistical baseline ({base_num:,.2f}) using {algorithm.upper()} detection."
                    ),
                    "metric_name": metric_name,
                    "affected_dimension": dimension_name,
                    "affected_segment": period_str,
                    "severity": severity,
                    "baseline_value": f"{base_num:,.2f}",
                    "observed_value": f"{val_num:,.2f}",
                    "deviation_pct": dev_pct,
                    "detection_method": algorithm,
                    "anomaly_score": pt.anomaly_score,
                    "caveats": res.caveats_and_limitations,
                    "supporting_data": {
                        "algorithm": algorithm,
                        "anomaly_score": pt.anomaly_score,
                        "lower_bound": pt.lower_bound,
                        "upper_bound": pt.upper_bound,
                        "total_observations": res.total_records_analyzed,
                        "outlier_count": len(res.anomalous_points),
                    },
                })

        except Exception as err:
            logger.warning(f"Anomaly evaluation bypassed for {metric_name}: {err}")

        return findings
