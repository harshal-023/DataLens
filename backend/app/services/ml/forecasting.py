import math
import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from app.core.exceptions import DataLensException
from app.schemas.ml import ForecastPoint, ForecastResponse, HistoricalPoint


class ForecastingService:
    """
    Time-series forecasting with chronological validation, prediction intervals,
    and historical backtesting evaluation (MAE, RMSE, MAPE).
    """

    @classmethod
    def generate_forecast(
        cls,
        series_data: list[dict[str, Any]],
        target_column: str,
        time_column: str,
        forecast_horizon: int = 12,
        algorithm: str = "exponential_smoothing",
        confidence_level: float = 0.95,
        seasonality_period: int | None = None,
        model_run_id: uuid.UUID | None = None,
        dataset_id: uuid.UUID | None = None,
        dataset_version_id: uuid.UUID | None = None,
        duration_ms: int = 0,
    ) -> ForecastResponse:
        """
        Generates forward-looking projections and backtesting evaluation.
        """
        # Validate minimum observations
        min_required = max(6, (seasonality_period or 4) * 2)
        if len(series_data) < min_required:
            raise DataLensException(
                f"At least {min_required} chronological observations are required to generate time-series forecasts. Found {len(series_data)}.",
                code="INSUFFICIENT_DATA",
            )

        # 1. Sort chronologically by timestamp if available
        def parse_sort_key(pt):
            ts = pt.get("timestamp")
            if not ts:
                return pt.get("row_index", 0)
            try:
                return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except Exception:
                return str(ts)

        sorted_series = sorted(series_data, key=parse_sort_key)
        values = np.array([pt["value"] for pt in sorted_series], dtype=np.float64)
        timestamps = [str(pt.get("timestamp") or f"T{pt.get('row_index', i)}") for i, pt in enumerate(sorted_series)]

        # 2. Backtesting split (last 20% or max 5 points for validation)
        split_idx = max(4, int(len(values) * 0.8))
        train_vals = values[:split_idx]
        test_vals = values[split_idx:]

        # Fit model on training slice to compute backtest metrics
        backtest_preds = cls._project(train_vals, len(test_vals), algorithm, seasonality_period)
        mae, rmse, mape = cls._compute_metrics(test_vals, backtest_preds)

        # Baseline naive comparison (last observed value)
        naive_preds = np.full(len(test_vals), train_vals[-1])
        baseline_mae, _, _ = cls._compute_metrics(test_vals, naive_preds)

        # 3. Fit on full history and project forward horizon
        future_projections = cls._project(values, forecast_horizon, algorithm, seasonality_period)

        # 4. Compute prediction intervals based on historical residual standard deviation
        residuals = values[1:] - values[:-1]
        sigma = float(np.std(residuals)) if len(residuals) > 0 else 1.0
        z_multiplier = 1.96 if confidence_level >= 0.95 else 1.28

        # Generate forward timestamps
        future_timestamps = cls._extrapolate_timestamps(timestamps, forecast_horizon)

        historical_points = [
            HistoricalPoint(timestamp=ts, actual_value=round(float(v), 4))
            for ts, v in zip(timestamps, values, strict=False)
        ]

        forecast_points = []
        for i, (fut_ts, pred_val) in enumerate(zip(future_timestamps, future_projections, strict=False)):
            # Expanding uncertainty bounds over horizon
            uncertainty = z_multiplier * sigma * math.sqrt(i + 1)
            lower = max(0.0, float(pred_val - uncertainty))
            upper = float(pred_val + uncertainty)

            forecast_points.append(
                ForecastPoint(
                    period_index=i + 1,
                    timestamp=fut_ts,
                    forecast_value=round(float(pred_val), 4),
                    lower_bound=round(lower, 4),
                    upper_bound=round(upper, 4),
                )
            )

        explanation = cls._get_explanation(algorithm, forecast_horizon, confidence_level)
        caveats = [
            "Forecasts represent mathematical trend extrapolations, NOT guaranteed future commitments.",
            "External market shifts, policy changes, and black-swan shocks cannot be anticipated from historical series alone.",
            f"Backtest evaluation achieved MAE = {mae:.2f} across holdout observations.",
        ]

        return ForecastResponse(
            model_run_id=model_run_id or uuid.uuid4(),
            dataset_id=dataset_id or uuid.uuid4(),
            dataset_version_id=dataset_version_id or uuid.uuid4(),
            target_column=target_column,
            time_column=time_column,
            algorithm=algorithm,
            forecast_horizon=forecast_horizon,
            historical_points=historical_points,
            forecast_points=forecast_points,
            backtest_metrics={
                "mae": round(mae, 4) if mae is not None else None,
                "rmse": round(rmse, 4) if rmse is not None else None,
                "mape": round(mape, 2) if mape is not None else None,
            },
            baseline_comparison={
                "baseline_algorithm": "naive_last_observed",
                "baseline_mae": round(baseline_mae, 4) if baseline_mae is not None else None,
                "model_improvement_pct": round(((baseline_mae - mae) / baseline_mae) * 100, 1)
                if baseline_mae and baseline_mae > 0 else 0.0,
            },
            method_explanation=explanation,
            caveats_and_limitations=caveats,
            execution_time_ms=duration_ms,
        )

    @classmethod
    def _project(
        cls,
        history: np.ndarray,
        horizon: int,
        algorithm: str,
        seasonality: int | None,
    ) -> np.ndarray:
        n = len(history)
        if horizon <= 0:
            return np.array([])

        if algorithm == "moving_average":
            window = min(n, 5)
            rolling = list(history)
            preds = []
            for _ in range(horizon):
                nxt = float(np.mean(rolling[-window:]))
                preds.append(nxt)
                rolling.append(nxt)
            return np.array(preds)

        elif algorithm == "exponential_smoothing":
            # Simple / Holt's linear trend smoothing
            alpha = 0.3
            beta = 0.1
            level = history[0]
            trend = (history[-1] - history[0]) / max(1, n - 1)

            for val in history:
                prev_level = level
                level = alpha * val + (1 - alpha) * (level + trend)
                trend = beta * (level - prev_level) + (1 - beta) * trend

            preds = [level + (i + 1) * trend for i in range(horizon)]
            return np.array(preds)

        elif algorithm == "seasonal_naive":
            season = seasonality or (7 if n >= 14 else 4)
            preds = []
            for i in range(horizon):
                cycle_idx = -(season - (i % season))
                preds.append(float(history[cycle_idx]))
            return np.array(preds)

        elif algorithm == "linear_trend":
            x = np.arange(n)
            slope, intercept = np.polyfit(x, history, 1)
            future_x = np.arange(n, n + horizon)
            return slope * future_x + intercept

        else:
            # Fallback to last observed
            return np.full(horizon, history[-1])

    @classmethod
    def _compute_metrics(
        cls,
        actuals: np.ndarray,
        predictions: np.ndarray,
    ) -> tuple[float, float, float | None]:
        if len(actuals) == 0 or len(predictions) == 0:
            return 0.0, 0.0, None

        min_len = min(len(actuals), len(predictions))
        y_true = actuals[:min_len]
        y_pred = predictions[:min_len]

        errors = y_true - y_pred
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))

        # MAPE with division-by-zero protection
        nonzero_mask = np.abs(y_true) > 1e-6
        if np.any(nonzero_mask):
            mape = float(np.mean(np.abs(errors[nonzero_mask] / y_true[nonzero_mask])) * 100.0)
        else:
            mape = None

        return mae, rmse, mape

    @classmethod
    def _extrapolate_timestamps(cls, timestamps: list[str], horizon: int) -> list[str]:
        if not timestamps:
            return [f"T+{i+1}" for i in range(horizon)]

        last_ts_str = timestamps[-1]
        try:
            # Try parsing ISO date
            last_date = datetime.fromisoformat(last_ts_str.replace("Z", "+00:00"))
            delta = timedelta(days=1)
            if len(timestamps) >= 2:
                try:
                    prev_date = datetime.fromisoformat(timestamps[-2].replace("Z", "+00:00"))
                    diff = (last_date - prev_date).total_seconds()
                    if diff > 0:
                        delta = timedelta(seconds=diff)
                except Exception:
                    pass

            return [(last_date + (i + 1) * delta).strftime("%Y-%m-%d") for i in range(horizon)]
        except Exception:
            return [f"{last_ts_str}+period{i+1}" for i in range(horizon)]

    @staticmethod
    def _get_explanation(algorithm: str, horizon: int, confidence: float) -> str:
        if algorithm == "exponential_smoothing":
            return (
                f"Holt's Linear Exponential Smoothing decomposes the time series into an evolving level and trend. "
                f"Projects {horizon} forward periods with {confidence*100:.0f}% confidence prediction intervals."
            )
        if algorithm == "moving_average":
            return (
                f"Moving Average extrapolates rolling window trends over {horizon} forward periods, "
                f"with widening uncertainty intervals representing compounding variance."
            )
        if algorithm == "seasonal_naive":
            return (
                f"Seasonal Naive projects cyclical patterns repeating historical seasonal cycles over a {horizon}-period horizon."
            )
        return f"Linear Trend projections extrapolate historical slope and intercept across {horizon} forward periods."
