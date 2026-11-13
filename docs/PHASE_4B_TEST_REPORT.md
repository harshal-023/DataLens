# DataLens Phase 4B Test Report & Verification Matrix

## Summary of Verification

| Category | Suite | Passed | Failed | Status |
|---|---|---|---|---|
| Backend Unit Tests | Formula Engine | 5 | 0 | **PASS** |
| Backend Integration | Pipelines, Steps, Joins, Run, RBAC | 1 | 0 | **PASS** |
| Full Backend Regression | Full Test Suite (`pytest`) | 175 | 0 | **PASS** |
| Backend Linting | `ruff check backend/app backend/tests` | All | 0 | **PASS** |
| Frontend Unit Tests | Vitest (`npm run test:frontend`) | 11 | 0 | **PASS** |
| Frontend Type Check & Bundle | Vite Build (`npm run build`) | Built in 15.07s | 0 | **PASS** |
| Database Migration | Alembic Revision `20261111_0007` | Applied | 0 | **PASS** |

---

## Detailed Test Cases

### 1. Formula Engine
- `test_formula_engine_basic_arithmetic`: Parses multi-term arithmetic `[price] * [quantity] * (1 - [discount])` and verifies AST and column identification. [PASS]
- `test_formula_engine_safe_division`: Verifies `/` converts to `NULLIF(denominator, 0)`. [PASS]
- `test_formula_engine_functions`: Verifies `IF()`, `UPPER()`, and string literal conversions. [PASS]
- `test_formula_engine_invalid_column`: Verifies formula referencing unprovided column raises `FormulaError`. [PASS]
- `test_formula_engine_unknown_function`: Verifies unauthorized function name raises `FormulaError`. [PASS]

### 2. Pipelines, Steps & End-to-End Execution
- `test_transformations_end_to_end`:
  - Dry-run formula validation endpoint (`/api/v1/transformations/validate-formula`). [PASS]
  - Create, List, and Retrieve Pipeline. [PASS]
  - Add Clean Nulls step (fill quantity with 1). [PASS]
  - Add Inner Join step (Join Orders with Customers on `customer_id` == `id`). [PASS]
  - Add Formula step (`total_amount = price * quantity`). [PASS]
  - Pipeline Preview endpoint: Executes DuckDB in-memory, returns 3 enriched rows with columns `total_amount` and `customer_name`. [PASS]
  - Execute Run Pipeline endpoint: Materializes derived Parquet dataset and manifest, updates `TransformationRun` status to `completed`. [PASS]
  - Verifies derived dataset is queryable in workspace. [PASS]
  - RBAC verification: Viewer role rejected with 403 on pipeline creation. [PASS]
  - Cross-workspace isolation: Foreign workspace rejected with 404. [PASS]

### 3. Frontend Vitest
- Formula expression column extraction regex. [PASS]
- Join key pair validation. [PASS]
- Conflict column suffix resolution (`_left`, `_right`). [PASS]
- Transformation step reordering without gap sequence. [PASS]
- Null strategy descriptors. [PASS]

