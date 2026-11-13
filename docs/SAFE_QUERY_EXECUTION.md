# Safe Query Execution Engine

## Security Architecture
DataLens strictly separates the non-deterministic natural language layer from deterministic query execution. LLMs are never permitted to emit executable SQL, Python, or shell code.

## Protection Mechanisms

### 1. Whitelist Identifier Sanitization
All column identifiers, dataset names, and table aliases pass through `sanitize_identifier`:
```python
@classmethod
def sanitize_identifier(cls, name: str) -> str:
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        raise DataLensException(f"Invalid column identifier: '{name}'.", code="INVALID_COLUMN")
    return f'"{name}"'
```
Any characters outside alphanumeric and underscores (e.g. `;`, `'`, `"`, `--`, `/*`) trigger immediate execution abortion.

### 2. Parameterized Filter Execution
All dynamic filter values use parameterized SQL placeholders (`?`), preventing SQL injection attacks regardless of user input.

### 3. Division-by-Zero Protection
Mathematical ratios and formulas enforce zero-denominator protection:
```sql
SUM(revenue) / NULLIF(SUM(cost), 0)
```

### 4. Read-Only Parquet Scans
Queries run solely against verified, immutable Parquet files via DuckDB's `read_parquet(...)` reader. No write operations or modifications to storage occur.

### 5. Multi-Tenant Execution Boundaries
- DuckDB thread throttling: `PRAGMA threads=4;`
- Memory ceiling: `PRAGMA memory_limit='2GB';`
- Strict 30-second query timeout.
- Maximum row limit capped at 1,000 rows.

