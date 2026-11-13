# Anomaly Intelligence

## Overview
The `AnomalyEngine` in Phase 6D builds upon the Phase 3C `AnomalyDetectionService` to proactively detect statistical and business outliers across multidimensional slices.

## Detection Algorithms
1. **Z-Score (Gaussian Distribution)**:
   - Identifies data points where:
     $$|z| = \left|\frac{x - \mu}{\sigma}\right| > 3.0$$
   - Effective for normally distributed time-series metrics like daily order volume or standard operational processing times.

2. **Interquartile Range (IQR - Robust to Skew)**:
   - Computes:
     $$\text{IQR} = Q_3 - Q_1$$
     $$\text{Lower Bound} = Q_1 - 1.5 \times \text{IQR}, \quad \text{Upper Bound} = Q_3 + 1.5 \times \text{IQR}$$
   - Handles asymmetric distributions such as deal sizes, transaction values, or user session lengths.

3. **Isolation Forest (Multivariate Isolation)**:
   - Isolates multidimensional anomalies combining revenue, discount %, and quantity in high-dimensional feature spaces.

## Anomaly Metadata & Caveat Propagation
Each anomaly point extracted by the engine includes:
- `timestamp`: Observation date/time.
- `actual_value`: The observed measurement.
- `expected_value`: Expected baseline / rolling median.
- `deviation_pct`: Percentage deviation from baseline.
- `caveats_and_limitations`: Contextual alerts (e.g., holiday seasonality, sample size limitations, data sparsity warnings).

