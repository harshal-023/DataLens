# DataLens — Anomaly Detection Architecture & Mathematical Foundations

## 1. Executive Summary

DataLens Phase 3C implements deterministic statistical anomaly detection directly integrated with the DuckDB and Parquet analytics layers. The system enables business users to audit tabular and time-series data for operational outliers without requiring custom Python code or unverified black-box predictions.

Every detected outlier is accompanied by:
1. Exact row index and timestamp provenance.
2. Inferred expected baseline value.
3. Upper and lower statistical threshold bounds.
4. Normalized anomaly severity score (`low`, `medium`, `high`).
5. Mathematical methodology explanation and explicit operational caveats.

---

## 2. Supported Algorithms & Formulations

### 2.1 Z-Score (Standard Score)

**Applicability:** Recommended for approximately normal, unimodal numerical distributions with moderate to large sample sizes ($N \ge 10$).

**Mathematical Formulation:**
Given sample observations $X = \{x_1, x_2, \dots, x_N\}$:
$$\mu = \frac{1}{N} \sum_{i=1}^N x_i$$
$$\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (x_i - \mu)^2}$$

The standardized Z-score for observation $x_i$ is:
$$z_i = \frac{|x_i - \mu|}{\sigma}$$

**Thresholding:**
For a configured sensitivity parameter $S \in [1.0, 4.0]$ (default $S = 2.5$):
- An observation is flagged as an anomaly if $z_i > S$.
- Upper Bound: $B_{\text{upper}} = \mu + S \cdot \sigma$
- Lower Bound: $B_{\text{lower}} = \mu - S \cdot \sigma$

**Severity Scoring:**
- `high`: $z_i \ge 4.0$
- `medium`: $3.0 \le z_i < 4.0$
- `low`: $S < z_i < 3.0$

**Zero-Variance Handling:**
If all values are identical ($\sigma = 0$), the service returns 0 anomalies without division-by-zero errors.

---

### 2.2 Interquartile Range (IQR)

**Applicability:** Recommended for skewed distributions, financial data, long-tailed metrics, and datasets with pre-existing extreme values.

**Mathematical Formulation:**
Observations are sorted in ascending order.
- First Quartile ($Q_1$): 25th percentile.
- Median: 50th percentile.
- Third Quartile ($Q_3$): 75th percentile.
$$\text{IQR} = Q_3 - Q_1$$

**Thresholding:**
For a multiplier $M = S$ (where $S \in [1.0, 3.0]$, default $S = 1.5$):
$$B_{\text{lower}} = Q_1 - (M \cdot \text{IQR})$$
$$B_{\text{upper}} = Q_3 + (M \cdot \text{IQR})$$

An observation $x_i$ is anomalous if:
$$x_i < B_{\text{lower}} \quad \text{or} \quad x_i > B_{\text{upper}}$$

**Anomaly Score:**
$$\text{Score}_i = \frac{\max(B_{\text{lower}} - x_i, x_i - B_{\text{upper}})}{\max(\text{IQR}, 1.0)}$$

---

### 2.3 Isolation Forest

**Applicability:** Multidimensional or non-linear distributions where anomalies are isolated closer to the root in randomly generated decision trees.

**Mathematical Formulation:**
The algorithm constructs an ensemble of $T = 100$ isolation trees ($iTrees$).
The path length $h(x)$ to isolate observation $x$ measures normality:
$$s(x, n) = 2^{-\frac{\mathbb{E}(h(x))}{c(n)}}$$
where $c(n) = 2 \ln(n - 1) + 0.5772156649 - \frac{2(n-1)}{n}$ is the average path length of unsuccessful searches in a Binary Search Tree.

**Contamination Mapping:**
Sensitivity $S \in [0.5, 5.0]$ maps to target contamination rate:
$$C = \max\left(0.01, \min\left(0.20, \frac{S}{25.0}\right)\right)$$

---

## 3. Ethical Safeguards & Caveats

DataLens enforces strict presentation guidelines for statistical anomalies:
1. **Never Presume Malfeasance:** Statistical outliers indicate mathematical divergence from historical distributions; they do NOT confirm fraud, accounting errors, or bad behavior.
2. **Context Requirement:** Outliers often reflect genuine business milestones (e.g., Black Friday sales spikes, viral product launches).
3. **Auditing Record:** Every anomaly detection execution writes an immutable `ModelRun` entry into PostgreSQL recording timestamp, parameters, user ID, workspace ID, dataset version, and full summary metrics.

