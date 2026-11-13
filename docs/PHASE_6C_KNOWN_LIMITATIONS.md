# Phase 6C Known Limitations & Future Roadmap

## Known Limitations

### 1. Complex Nested Joins Beyond Two Datasets
- **Current Behavior**: The current `NLASafeQueryCompiler` supports single-hop joins between primary and secondary datasets via registered relationships.
- **Roadmap**: Multi-hop joins across 3+ normalized star/snowflake schema tables are targeted for future expansion.

### 2. Full-Text Free-Form Fuzzy Value Matching
- **Current Behavior**: Categorical filters match via `ILIKE '%value%'` over dimension columns detected in the semantic layer.
- **Roadmap**: Implementing trigram-based embedding search over low-cardinality dimension dictionaries to catch minor spelling variations.

### 3. Asynchronous DuckDB Query Cancellation
- **Current Behavior**: Queries are bounded by a 30-second timeout. If interrupted by the user, the connection closes on completion.
- **Roadmap**: Adding explicit client-side abort controllers wired to DuckDB connection interrupt signals.

### 4. Non-Standard Custom Calendar Cycles
- **Current Behavior**: Supports daily, weekly, monthly, quarterly, and yearly intervals.
- **Roadmap**: 4-4-5 and custom fiscal 52-week calendars will be introduced with enterprise organization fiscal profile settings.

