import math
import uuid
from typing import Any

import numpy as np

from app.core.exceptions import DataLensException
from app.schemas.ml import AnomalyDetectResponse, AnomalyPoint


class AnomalyDetectionService:
    """
    Deterministic anomaly detection supporting Z-score, IQR, and Isolation Forest.
    Strictly distinguishes statistical variance from confirmed business fraud or operational defects.
    """

    @classmethod
    def detect_anomalies(
        cls,
        series_data: list[dict[str, Any]],
        target_column: str,
        algorithm: str = "z_score",
        sensitivity: float = 2.5,
        max_anomalies_return: int = 100,
        model_run_id: uuid.UUID | None = None,
        dataset_id: uuid.UUID | None = None,
        dataset_version_id: uuid.UUID | None = None,
        duration_ms: int = 0,
    ) -> AnomalyDetectResponse:
        """
        Executes anomaly detection algorithm over extracted series.
        """
        if len(series_data) < 5:
            raise DataLensException(
                "At least 5 numerical observations are required for anomaly detection.",
                code="INSUFFICIENT_DATA",
            )

        values = np.array([pt["value"] for pt in series_data], dtype=np.float64)
        total_records = len(values)

        if algorithm == "z_score":
            anomalous_points, summary, explanation, caveats = cls._detect_zscore(
                series_data, values, sensitivity, max_anomalies_return
            )
        elif algorithm == "iqr":
            anomalous_points, summary, explanation, caveats = cls._detect_iqr(
                series_data, values, sensitivity, max_anomalies_return
            )
        elif algorithm == "isolation_forest":
            anomalous_points, summary, explanation, caveats = cls._detect_isolation_forest(
                series_data, values, sensitivity, max_anomalies_return
            )
        else:
            raise DataLensException(
                f"Unsupported anomaly detection algorithm '{algorithm}'. Choose 'z_score', 'iqr', or 'isolation_forest'.",
                code="INVALID_ALGORITHM",
            )

        pct = round((len(anomalous_points) / total_records) * 100, 2) if total_records > 0 else 0.0

        return AnomalyDetectResponse(
            model_run_id=model_run_id or uuid.uuid4(),
            dataset_id=dataset_id or uuid.uuid4(),
            dataset_version_id=dataset_version_id or uuid.uuid4(),
            target_column=target_column,
            algorithm=algorithm,
            total_records_analyzed=total_records,
            anomalies_detected_count=len(anomalous_points),
            anomaly_percentage=pct,
            summary_metrics=summary,
            anomalous_points=anomalous_points[:max_anomalies_return],
            detection_method_explanation=explanation,
            caveats_and_limitations=caveats,
            execution_time_ms=duration_ms,
        )

    @classmethod
    def _detect_zscore(
        cls,
        series: list[dict[str, Any]],
        values: np.ndarray,
        sensitivity: float,
        limit: int,
    ) -> tuple[list[AnomalyPoint], dict[str, Any], str, list[str]]:
        mean_val = float(np.mean(values))
        std_val = float(np.std(values))

        if std_val == 0.0 or math.isnan(std_val):
            return [], {"mean": mean_val, "std": 0.0}, "Standard deviation is zero; no statistical variance exists.", []

        z_cutoff = max(1.0, float(sensitivity))
        lower_bound = mean_val - (z_cutoff * std_val)
        upper_bound = mean_val + (z_cutoff * std_val)

        anomalies: list[AnomalyPoint] = []
        for idx, pt in enumerate(series):
            val = pt["value"]
            z = round(abs(val - mean_val) / std_val, 4) if std_val > 0 else 0.0
            if z > z_cutoff:
                if z >= 4.0:
                    severity = "high"
                elif z >= 3.0:
                    severity = "medium"
                else:
                    severity = "low"

                anomalies.append(
                    AnomalyPoint(
                        row_index=pt.get("row_index", idx),
                        timestamp=pt.get("timestamp"),
                        actual_value=round(val, 4),
                        expected_value=round(mean_val, 4),
                        lower_bound=round(lower_bound, 4),
                        upper_bound=round(upper_bound, 4),
                        anomaly_score=round(z, 3),
                        severity=severity,
                        is_anomaly=True,
                    )
                )

        # Sort by anomaly score descending
        anomalies.sort(key=lambda a: a.anomaly_score, reverse=True)

        summary = {
            "mean": round(mean_val, 4),
            "std": round(std_val, 4),
            "z_threshold": round(z_cutoff, 2),
            "lower_bound": round(lower_bound, 4),
            "upper_bound": round(upper_bound, 4),
        }
        explanation = (
            f"Z-score detection standardizes values against the sample mean ({mean_val:.2f}) and standard deviation ({std_val:.2f}). "
            f"Values deviating by more than {z_cutoff:.1f} standard deviations are flagged as statistical anomalies."
        )
        caveats = [
            "Statistical outliers reflect unusual variance and must not be assumed to indicate fraud or errors without operational verification.",
            "Z-score assumes approximate normal distribution; heavily skewed distributions may yield asymmetric false positives.",
        ]
        return anomalies, summary, explanation, caveats

    @classmethod
    def _detect_iqr(
        cls,
        series: list[dict[str, Any]],
        values: np.ndarray,
        sensitivity: float,
        limit: int,
    ) -> tuple[list[AnomalyPoint], dict[str, Any], str, list[str]]:
        q1 = float(np.percentile(values, 25))
        median = float(np.median(values))
        q3 = float(np.percentile(values, 75))
        iqr = q3 - q1

        multiplier = max(0.5, float(sensitivity))
        lower_bound = q1 - (multiplier * iqr)
        upper_bound = q3 + (multiplier * iqr)

        anomalies: list[AnomalyPoint] = []
        for idx, pt in enumerate(series):
            val = pt["value"]
            if val < lower_bound or val > upper_bound:
                dist = max(lower_bound - val, val - upper_bound)
                score = round(dist / (iqr if iqr > 0 else 1.0), 3)

                severity = "high" if score >= 2.0 else "medium" if score >= 1.0 else "low"
                anomalies.append(
                    AnomalyPoint(
                        row_index=pt.get("row_index", idx),
                        timestamp=pt.get("timestamp"),
                        actual_value=round(val, 4),
                        expected_value=round(median, 4),
                        lower_bound=round(lower_bound, 4),
                        upper_bound=round(upper_bound, 4),
                        anomaly_score=score,
                        severity=severity,
                        is_anomaly=True,
                    )
                )

        anomalies.sort(key=lambda a: a.anomaly_score, reverse=True)

        summary = {
            "median": round(median, 4),
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "multiplier": round(multiplier, 2),
            "lower_bound": round(lower_bound, 4),
            "upper_bound": round(upper_bound, 4),
        }
        explanation = (
            f"Interquartile Range (IQR) detection is non-parametric and robust against skewed data. "
            f"Values outside [{lower_bound:.2f}, {upper_bound:.2f}] (Q1/Q3 +/- {multiplier:.1f}*IQR) are flagged."
        )
        caveats = [
            "IQR is robust to non-normal distributions but does not consider time-dependent trend patterns.",
            "Extreme bounds do not necessarily imply unbusinesslike behavior.",
        ]
        return anomalies, summary, explanation, caveats

    @classmethod
    def _detect_isolation_forest(
        cls,
        series: list[dict[str, Any]],
        values: np.ndarray,
        sensitivity: float,
        limit: int,
    ) -> tuple[list[AnomalyPoint], dict[str, Any], str, list[str]]:
        from sklearn.ensemble import IsolationForest

        # Map sensitivity (0.5 to 5.0) to contamination (0.01 to 0.15)
        contamination = max(0.01, min(0.20, (sensitivity / 25.0)))
        X = values.reshape(-1, 1)

        clf = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        preds = clf.fit_predict(X)  # -1 for anomaly, 1 for normal
        decision_scores = clf.decision_function(X)  # Lower is more abnormal

        anomalies: list[AnomalyPoint] = []
        for _idx, (pt, pred, score) in enumerate(zip(series, preds, decision_scores, strict=False)):
            if pred == -1:
                val = pt["value"]
                # Convert decision score to positive abnormality magnitude
                norm_score = round(float(abs(score)), 3)
                severity = "high" if norm_score >= 0.20 else "medium" if norm_score >= 0.10 else "low"

                anomalies.append(
                    AnomalyPoint(
                        row_index=pt.get("row_index", _idx),
                        timestamp=pt.get("timestamp"),
                        actual_value=round(val, 4),
                        expected_value=round(float(np.mean(values)), 4),
                        lower_bound=None,
                        upper_bound=None,
                        anomaly_score=norm_score,
                        severity=severity,
                        is_anomaly=True,
                    )
                )

        anomalies.sort(key=lambda a: a.anomaly_score, reverse=True)

        summary = {
            "contamination_rate": round(contamination, 3),
            "n_estimators": 100,
            "mean_decision_score": round(float(np.mean(decision_scores)), 4),
        }
        explanation = (
            f"Isolation Forest isolates anomalies by randomly partitioning feature dimensions into trees. "
            f"Anomalous observations require fewer splits to isolate (contamination target: {contamination*100:.1f}%)."
        )
        caveats = [
            "Tree partitioning is stochastic; identical scores may vary slightly across runs without fixed random seed.",
            "Isolation Forest identifies geometric separation without domain context.",
        ]
        return anomalies, summary, explanation, caveats
