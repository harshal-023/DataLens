# Metric Intelligence Engine & Formula Validator

## 1. Overview
The [`MetricIntelligenceEngine`](file:///d:/PE%20CP/backend/app/services/intelligence/metric_engine.py) provides a safe, reusable mathematical formula compiler and execution engine for enterprise business metrics. It protects the platform against code injection, prevents runtime division-by-zero crashes, and provides full version audit trails.

---

## 2. Safe Formula Parsing (Zero `eval` / Zero `exec`)

The formula parser parses expressions using Python's `ast.parse(clean, mode="eval")`. It utilizes a strict node whitelist ([`SafeFormulaValidator`](file:///d:/PE%20CP/backend/app/services/intelligence/metric_engine.py)):

### Permitted AST Nodes:
- Constants: Numbers (`10`, `0.05`, `100`).
- Arithmetic Operators: `+`, `-`, `*`, `/`, `-x` (unary minus).
- Valid Identifiers: Column names, registered metric names.
- Allowed Aggregate Functions: `SUM()`, `AVG()`, `COUNT()`, `MIN()`, `MAX()`, `ROUND()`, `ABS()`, `COALESCE()`.

### Blocked Constructs:
- Any Python statement (`import`, `def`, `class`, `exec`, `eval`, `lambda`).
- System/process calls (`subprocess`, `os.system`).
- String literals, quotes (`"` or `'`), backticks, semicolons.
- Arbitrary method calls or attribute access (`x.format()`, `__class__`).

---

## 3. Automatic Division-by-Zero Protection

When compiling a formula to DuckDB SQL, all division operators are automatically wrapped with `NULLIF(denominator, 0)`:
```
Formula:  Revenue / Total_Orders * 100
SQL:      SELECT (Revenue / NULLIF(Total_Orders, 0) * 100) FROM read_parquet(...)
```
If `Total_Orders` is zero or null, DuckDB returns `NULL` rather than raising a fatal runtime exception.

---

## 4. Metric Versioning & Audit History

Metrics are versioned to preserve historical provenance:
- Each change to a metric's formula increments its `version` integer (v1 -> v2).
- An immutable snapshot is appended to the `metric_versions` table containing:
  - `metric_id`
  - `version_number`
  - `formula`
  - `source_columns`
  - `formatting`
  - `change_summary`
  - `created_by_user_id`
  - `created_at`
- Reports and dashboards utilizing previous versions maintain valid calculations and are protected from unannounced formula changes.

---

## 5. Live DuckDB Calculation API
- `POST /api/v1/metrics/validate`: Validates formula syntax, returns referenced columns, errors, and compiled SQL.
- `POST /api/v1/metrics/calculate`: Directly executes the formula against dataset Parquet parts, returning the calculated float result and execution status.

