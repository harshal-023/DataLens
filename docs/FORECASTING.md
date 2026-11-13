# DataLens — Time-Series Forecasting Architecture & Methodology

## 1. Overview

The DataLens Forecasting Service generates forward-looking projections from chronological historical observations stored in Parquet format. Projections are accompanied by:
- Chronologically validated historical backtesting evaluation (MAE, RMSE, MAPE).
- Dynamic statistical prediction intervals ($80\%$, $90\%$, $95\%$, $99\%$).
- Model provenance and parameter auditing via `ModelRun` records.
- Grounded narrative business insights via `BusinessInsightEngine`.

---

## 2. Algorithms & Mathematical Formulations

Given chronological historical series $Y = [y_1, y_2, \dots, y_T]$ and forecast horizon $h \ge 1$:

### 2.1 Exponential Smoothing (Single)

**Applicability:** Data with a consistent level and mild trend without complex seasonal components.

**Equation:**
$$\hat{y}_{t+1} = \alpha y_t + (1 - \alpha) \hat{y}_t$$
where smoothing factor $\alpha \in (0, 1)$ (default $\alpha = 0.3$).

**Forward Extrapolation:**
$$\hat{y}_{T+k} = \hat{y}_{T+1} \quad \text{for } k = 1, \dots, h$$

**Prediction Interval:**
For confidence level $1 - \beta$ with critical value $Z_{\beta/2}$:
$$\text{Margin}_k = Z_{\beta/2} \cdot \sigma_e \cdot \sqrt{1 + (k - 1) \alpha^2}$$
$$\text{Lower Bound} = \hat{y}_{T+k} - \text{Margin}_k$$
$$\text{Upper Bound} = \hat{y}_{T+k} + \text{Margin}_k$$

---

### 2.2 Rolling Moving Average

**Applicability:** Smoothing noisy demand signals and short-term volatility.

**Equation:**
For rolling window $W = \min(5, \lfloor T/2 \rfloor)$:
$$\hat{y}_{T+k} = \frac{1}{W} \sum_{i=0}^{W-1} y_{T-i}$$

---

### 2.3 Seasonal Naive

**Applicability:** Periodic time series with strong recurring cycles (e.g., weekly day-of-week $P = 7$, monthly $P = 12$, quarterly $P = 4$).

**Equation:**
For seasonality period $P$:
$$\hat{y}_{T+k} = y_{T + k - P \cdot \lceil k/P \rceil}$$
Each forecasted period replicates the corresponding historical observation from the most recent completed cycle.

---

### 2.4 Linear Trend (Ordinary Least Squares)

**Applicability:** Series with steady secular growth or decline.

**Equation:**
$$\hat{y}_t = \beta_0 + \beta_1 t$$
where:
$$\beta_1 = \frac{\sum_{t=1}^T (t - \bar{t})(y_t - \bar{y})}{\sum_{t=1}^T (t - \bar{t})^2}$$
$$\beta_0 = \bar{y} - \beta_1 \bar{t}$$

---

## 3. Backtesting & Model Evaluation

To prevent ungrounded extrapolation, DataLens automatically evaluates the chosen algorithm on the most recent chronological observations before generating forward projections:

1. **Split Point:** Data is partitioned into training ($80\%$) and testing ($20\%$).
2. **Evaluation Metrics:**
   - **Mean Absolute Error (MAE):**
     $$\text{MAE} = \frac{1}{n} \sum_{i=1}^n |y_i - \hat{y}_i|$$
   - **Root Mean Squared Error (RMSE):**
     $$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^n (y_i - \hat{y}_i)^2}$$
   - **Mean Absolute Percentage Error (MAPE):**
     $$\text{MAPE} = \frac{100\%}{n} \sum_{i=1}^n \left| \frac{y_i - \hat{y}_i}{y_i} \right|$$

---

## 4. Limitations & Best Practices

1. **Minimum History:** At least 6 chronological points are strictly required; seasonal naive models require at least $2 \times P$ observations.
2. **Stationarity:** Structural breaks, regulatory shifts, or macroeconomic shocks can violate statistical assumptions.
3. **No Guarantee:** Projections must never be presented as guaranteed financial outcomes.

