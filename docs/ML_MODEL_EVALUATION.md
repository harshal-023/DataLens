# DataLens — Machine Learning Model Evaluation Framework

## 1. Purpose & Standards

This document establishes the evaluation standards and verification protocols used by DataLens Phase 3C across anomaly detection, time-series forecasting, customer segmentation, and generative business insights.

The platform enforces three non-negotiable principles:
1. **Mathematical Grounding:** All metrics, scores, intervals, and cluster centroids are derived deterministically using verified Python libraries (`numpy`, `scipy`, `scikit-learn`, `duckdb`).
2. **Provenance & Auditability:** Every model execution creates an immutable `ModelRun` record in PostgreSQL capturing dataset version, algorithm parameters, execution duration, and quantitative metrics.
3. **No Hallucinated Predictions:** AI narrative generators (`BusinessInsightEngine`) are strictly constrained to factual reporting of computed outputs; they never extrapolate unsupported numbers.

---

## 2. Evaluation Criteria Matrix

| Model Family | Primary Metric | Target / Benchmark | Action on Degradation |
| :--- | :--- | :--- | :--- |
| **Anomaly Detection** | Outlier Incidence Rate ($\%$) | Typically $1\% - 5\%$ of sample | If rate $> 15\%$, warn user of high sensitivity setting |
| **Anomaly Detection** | Score Calibration | Monotonically increasing severity | Standardize scores to $[0, \infty)$ or $[0, 1]$ |
| **Forecasting** | Backtest MAE & RMSE | Non-negative, bounded scale | Flag large discrepancy between train and test error |
| **Forecasting** | Backtest MAPE | $< 15\%$ (Good), $< 30\%$ (Acceptable) | If $> 50\%$, recommend alternative algorithm or horizon |
| **Segmentation** | Silhouette Score | $> 0.25$ (Valid), $> 0.50$ (Strong) | Warn if score $< 0.20$ that clusters are diffuse |
| **Segmentation** | Cluster Size Balance | Min cluster $\ge 5\%$ of population | Avoid trivial outlier clusters with 1 observation |
| **Insight Synthesis** | Factual Precision | $100\%$ grounding in metrics JSON | Discard narrative if ungrounded claims are detected |

---

## 3. Provenance & Downloadable Reporting

For every completed model execution, DataLens supports four downloadable report formats:
- **PDF:** Executive summary with stylized tables, provenance badges, and DataLens color tokens (`#102C46`, `#009F98`).
- **DOCX:** Structured Word report suitable for formal enterprise review.
- **XLSX:** Formatted multi-tab spreadsheet including raw point projections, confidence bounds, or cluster centroid breakdowns.
- **CSV:** High-density export for downstream ingestion into BI tools.

