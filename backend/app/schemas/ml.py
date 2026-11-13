import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# =========================================================================
# ANOMALY DETECTION SCHEMAS
# =========================================================================

class AnomalyDetectRequest(BaseModel):
    dataset_id: uuid.UUID
    version_id: uuid.UUID | None = None
    target_column: str = Field(min_length=1, max_length=100)
    time_column: str | None = None
    algorithm: Literal["z_score", "iqr", "isolation_forest"] = "z_score"
    sensitivity: float = Field(default=2.5, ge=0.5, le=5.0)  # Z-score cutoff or IQR multiplier or IF contamination
    max_anomalies_return: int = Field(default=100, ge=1, le=1000)


class AnomalyPoint(BaseModel):
    row_index: int
    timestamp: str | None = None
    actual_value: float
    expected_value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    anomaly_score: float  # Absolute Z-score, distance, or IF score
    severity: Literal["low", "medium", "high"]
    is_anomaly: bool = True


class AnomalyDetectResponse(BaseModel):
    model_run_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    target_column: str
    algorithm: str
    total_records_analyzed: int
    anomalies_detected_count: int
    anomaly_percentage: float
    summary_metrics: dict[str, Any]  # mean, std, q1, q3, iqr, contamination
    anomalous_points: list[AnomalyPoint]
    detection_method_explanation: str
    caveats_and_limitations: list[str]
    execution_time_ms: int


# =========================================================================
# TIME-SERIES FORECASTING SCHEMAS
# =========================================================================

class ForecastRequest(BaseModel):
    dataset_id: uuid.UUID
    version_id: uuid.UUID | None = None
    target_column: str = Field(min_length=1, max_length=100)
    time_column: str = Field(min_length=1, max_length=100)
    forecast_horizon: int = Field(default=12, ge=1, le=100)
    algorithm: Literal["moving_average", "exponential_smoothing", "seasonal_naive", "linear_trend"] = "exponential_smoothing"
    confidence_level: float = Field(default=0.95, ge=0.8, le=0.99)
    seasonality_period: int | None = Field(default=None, ge=2, le=365)


class HistoricalPoint(BaseModel):
    timestamp: str
    actual_value: float


class ForecastPoint(BaseModel):
    period_index: int
    timestamp: str
    forecast_value: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    model_run_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    target_column: str
    time_column: str
    algorithm: str
    forecast_horizon: int
    historical_points: list[HistoricalPoint]
    forecast_points: list[ForecastPoint]
    backtest_metrics: dict[str, float | None]  # mae, rmse, mape
    baseline_comparison: dict[str, Any]
    method_explanation: str
    caveats_and_limitations: list[str]
    execution_time_ms: int


# =========================================================================
# SEGMENTATION / CLUSTERING SCHEMAS
# =========================================================================

class SegmentationRequest(BaseModel):
    dataset_id: uuid.UUID
    version_id: uuid.UUID | None = None
    feature_columns: list[str] = Field(min_length=1, max_length=20)
    algorithm: Literal["kmeans", "hierarchical"] = "kmeans"
    cluster_count: int = Field(default=3, ge=2, le=10)
    scale_features: bool = True
    cluster_label_prefix: str = "Segment"

    @field_validator("feature_columns")
    @classmethod
    def validate_features(cls, v: list[str]) -> list[str]:
        # Filter sensitive attributes
        prohibited = {"race", "ethnicity", "religion", "gender", "sex", "orientation", "disability", "ssn", "password"}
        for f in v:
            if f.lower() in prohibited:
                raise ValueError(f"Feature '{f}' is sensitive and prohibited from clustering.")
        return v


class ClusterProfile(BaseModel):
    cluster_id: int
    cluster_name: str
    record_count: int
    percentage: float
    feature_means: dict[str, float]
    feature_minima: dict[str, float]
    feature_maxima: dict[str, float]
    characterization: str


class SegmentationResponse(BaseModel):
    model_run_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    algorithm: str
    cluster_count: int
    total_records_clustered: int
    feature_columns: list[str]
    clusters: list[ClusterProfile]
    silhouette_score: float | None
    inertia: float | None
    segment_comparison_summary: str
    method_explanation: str
    caveats_and_limitations: list[str]
    execution_time_ms: int


# =========================================================================
# MODEL RUN & INSIGHT SCHEMAS
# =========================================================================

class ModelRunListItem(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    model_type: str
    algorithm: str
    status: str
    parameters: dict[str, Any]
    feature_columns: list[str]
    metrics: dict[str, Any]
    duration_ms: int
    created_at: datetime


class ModelRunDetailResponse(ModelRunListItem):
    result_summary: dict[str, Any]
    ai_insight: str | None = None


class GenerateInsightRequest(BaseModel):
    audience: Literal["executive", "analyst", "operational"] = "executive"
    include_recommendations: bool = True


class InsightResponse(BaseModel):
    model_run_id: uuid.UUID
    insight_narrative: str
    key_findings: list[str]
    limitations: list[str]
    suggested_actions: list[str]
    is_ai_generated: bool = False
    is_ai_generated: bool
