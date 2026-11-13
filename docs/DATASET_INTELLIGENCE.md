# Dataset Intelligence Profiler Technical Reference

## 1. Overview
The [`DatasetIntelligenceProfiler`](file:///d:/PE%20CP/backend/app/services/intelligence/profiler.py) performs high-performance, bounded statistical profiling of immutable Parquet dataset files using DuckDB. It extracts distributional metrics, identifies keys, and classifies columns into rich semantic types without loading entire tables into RAM.

---

## 2. Statistical Metrics Extracted per Column

| Metric Category | Computed Statistics |
| :--- | :--- |
| **Cardinality & Nulls** | Total rows, non-null count, null count, null percentage (`null_pct`), distinct count (`distinct_count`), uniqueness ratio (`uniqueness_pct`). |
| **Numeric Distributions** | Minimum, maximum, sample mean, sample standard deviation (`stddev`), first quartile (`q1`), median (`q2`), third quartile (`q3`), interquartile range (`iqr`). |
| **Outlier Detection** | IQR-based outlier counting (`value < q1 - 1.5 * iqr` or `value > q3 + 1.5 * iqr`). |
| **Temporal Distributions** | Minimum date, maximum date, date range. |
| **Categorical Profiles** | Top 10 most frequent discrete values with exact counts and percentage shares of total records. |
| **Duplicate Rows** | Exact duplicate row count estimated via DuckDB `COUNT(*) - COUNT(DISTINCT hash(*))`. |

---

## 3. Multi-Signal Semantic Classification

Columns are never classified solely from their name. Classification combines column tokens, physical DuckDB types, cardinality ratios, sample contents, and numeric distributions:

1. **`currency`**: Names with `revenue`, `price`, `cost`, `amount`, `sales`, `salary`, `mrp`, `discount` combined with numeric physical types (`DOUBLE`, `FLOAT`, `DECIMAL`, `BIGINT`).
2. **`percentage`**: Names with `pct`, `percent`, `rate`, `ratio`, `margin` or continuous values bounded strictly between `0.0` and `1.0` or `0.0` and `100.0`.
3. **`quantity`**: Names with `qty`, `quantity`, `units`, `items`, `count`, `stock` with non-negative integer or float types.
4. **`date` & `timestamp`**: Physical date/timestamp types, names matching `date`, `time`, `created_at`, or sample values matching ISO date patterns (`YYYY-MM-DD`).
5. **`customer_identifier`**: Column names matching `customer_id`, `client_id`, `user_id`, `buyer_id`.
6. **`product_identifier`**: Column names matching `product_id`, `item_id`, `sku`, `barcode`, `upc`.
7. **`transaction_identifier`**: Column names matching `order_id`, `transaction_id`, `invoice_id`, `receipt_id`.
8. **`email`**: Column name containing `email` or sample values matching RFC 5322 regex.
9. **`phone`**: Column name containing `phone`, `mobile`, `tel` or formatted phone number strings.
10. **`geographic_region`**: Column names matching `country`, `state`, `city`, `zip`, `postal`, `region`, `province`.
11. **`address`**: Column names matching `address`, `street`, `line1`.
12. **`status`**: Discrete categorical columns with names matching `status`, `state`, `stage`, `condition`.
13. **`category`**: Discrete categoricals (`distinct_count <= 25`) with names matching `category`, `department`, `segment`.

---

## 4. Key & Role Candidate Inference

- **Primary Key Candidate (`candidate_pks`)**:
  - `null_count == 0`
  - `distinct_count == total_rows` (100% uniqueness)
  - Logical type is `integer` or `string`
  - Non-boolean
- **Foreign Key Candidate (`candidate_fks`)**:
  - Suffix `_id`, `_key`, `_code`, or semantic classification is an identifier
  - Not marked as the primary key of this dataset
- **Measure vs. Dimension**:
  - Numeric continuous columns (`distinct_count > 10` or semantic type `currency`, `quantity`, `percentage`) are tagged as **Measures** with default aggregation `SUM` or `AVG`.
  - Temporal, categorical, identifier, and boolean columns are tagged as **Dimensions**.

---

## 5. Quality Score Formulation
Quality score starts at `100` and incurs bounded deductions based on verified anomalies:
- High missing rate (`> 50%` nulls): -15 points.
- Moderate missing rate (`20% - 50%` nulls): -7 points.
- Duplicate rows: -7 points.
- Suspicious negative values in positive measures (e.g. negative revenue or quantity): -7 points.
- Statistical outliers: -2 points.
- Constant columns (`distinct_count == 1`): -2 points.
Minimum quality score floor is `10`.

