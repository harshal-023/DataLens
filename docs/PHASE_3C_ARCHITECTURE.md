# DataLens — Phase 3C Architecture: Advanced AI Analytics, Machine Learning & Business Intelligence

## 1. Overview & Architectural Goals

Phase 3C extends DataLens with production-ready, deterministic machine learning and advanced analytical capabilities:
1. **Anomaly Detection**: Numerical and time-series anomaly detection (Z-score, IQR, Isolation Forest).
2. **Forecasting**: Time-series projection (Moving Average, Exponential Smoothing, Seasonal Naive, Linear Trend) with backtesting, prediction intervals, and error metrics (MAE, RMSE, MAPE).
3. **Segmentation**: Unsupervised clustering (K-Means, Hierarchical Clustering) with feature scaling, silhouette scoring, and cluster profiling.
4. **Business Insight Engine**: Executive narrative explanations powered by the existing `AIProvider` abstraction, strictly grounded in computed statistical outputs without hallucination.
5. **Model Run Management**: Persistent `model_runs` table in PostgreSQL tracking algorithm, hyperparameters, features, metrics, execution duration, and dataset version provenance.
6. **Reporting Integration**: Full PDF, DOCX, XLSX, and CSV report generation for advanced ML analyses.
7. **Interactive Frontend Experience**: Rich visualization of actuals vs. predictions, confidence bands, anomaly points, and cluster scatters adhering to DataLens design system (`#102C46`, `#009F98`, `#39C3B8`, `#DDF0F5`).

---

## 2. Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Layer                                 │
│  POST /api/v1/ml/anomaly    POST /api/v1/ml/forecast                   │
│  POST /api/v1/ml/segmentation   GET /api/v1/ml/runs   POST /insights   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   Anomaly Detection  │  │     Forecasting      │  │     Segmentation     │
│  - Z-Score           │  │  - Moving Average    │  │  - K-Means           │
│  - IQR Filtering     │  │  - Exp. Smoothing    │  │  - Agglomerative     │
│  - Isolation Forest  │  │  - Seasonal Naive    │  │  - Silhouette Score  │
└──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    DatasetDataLoader        │
                      │  - PyArrow / DuckDB Parquet │
                      │  - Missing-value handling   │
                      │  - Minimum row validation   │
                      └──────────────┬──────────────┘
                                     │
                ┌────────────────────┴────────────────────┐
                ▼                                         ▼
┌───────────────────────────────┐         ┌───────────────────────────────┐
│     PostgreSQL (SQLAlchemy)   │         │      AI Provider (LLM)        │
│  - model_runs                 │         │  - Narrative Interpretation   │
│  - Workspace isolation / RBAC │         │  - Limitations & Caveats      │
│  - Dataset Version Tracking   │         │  - Zero Output Alteration     │
└───────────────────────────────┘         └───────────────────────────────┘
```

---

## 3. Data Integrity & Ethics Standards

1. **Anomaly Attribution**: Anomalies are reported as statistical variances, never as confirmed business problems or fraud without verified external evidence.
2. **Forecasting Caution**: Forecasts always present historical backtest metrics and prediction intervals. Predictions are never presented as guaranteed future outcomes.
3. **Clustering Ethics**: Clusters represent mathematical feature groupings, not inherent psychological personas. Sensitive personal attributes (e.g., race, religion, gender) are excluded from clustering features.
4. **LLM Authority**: The LLM interprets verified numerical metrics; it cannot invent predictions or mutate model scores.

