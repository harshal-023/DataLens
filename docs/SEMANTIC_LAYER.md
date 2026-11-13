# Business Semantic Layer Reference

## 1. Overview
The DataLens Semantic Layer maps physical storage columns into clean, business-friendly terminology with unambiguous analytical roles (dimensions vs. measures), default aggregation strategies, and format masks.

---

## 2. Model Structure

### `ColumnSemanticMapping` Model:
```python
class ColumnSemanticMapping(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    dataset_version_id: UUID          # FK to immutable DatasetVersion
    dataset_id: UUID                  # FK to Dataset
    column_name: str                  # Physical column identifier (e.g. 'cust_order_amt')
    business_name: str                # Human-friendly business name (e.g. 'Customer Order Amount')
    semantic_type: str                # 'currency', 'percentage', 'quantity', 'email', etc.
    logical_type: str                 # 'string', 'integer', 'float', 'date', 'datetime', 'boolean'
    physical_type: str                # 'VARCHAR', 'DOUBLE', 'BIGINT', etc.
    aggregation_method: str           # 'SUM', 'AVG', 'COUNT', 'COUNT_DISTINCT', 'MIN', 'MAX', 'NONE'
    format_string: str                # 'USD', 'INR', 'PERCENT', 'INTEGER', 'DECIMAL'
    is_dimension: bool                # True if usable for group-by, slicing, or filtering
    is_measure: bool                  # True if usable for quantitative mathematical aggregation
    is_primary_key: bool              # True if uniquely identifies rows
    is_foreign_key: bool              # True if references another entity
    mapping_status: str               # 'AI_SUGGESTED', 'USER_CONFIRMED', 'SYSTEM_INFERRED'
    confidence_score: float           # 0.0 to 1.0
    confirmed_by_user_id: UUID        # User who confirmed/updated the definition
```

---

## 3. Human-Friendly Business Name Transformation
Technical column names in `snake_case`, `camelCase`, or containing common abbreviations are automatically transformed into professional titles using domain heuristics:
- `cust_order_amt` -> `Customer Order Amount`
- `product_sku` -> `Product SKU`
- `discount_pct` -> `Discount Percentage`
- `user_email` -> `User Email`
- `grossRevenueUSD` -> `Gross Revenue Usd`

---

## 4. User Confirmation & Preservation Invariant
DataLens adheres to a strict preservation rule:
**User-confirmed semantic mappings are NEVER overwritten by automated profiling or AI suggestions.**

When a user edits a business name, sets an aggregation method, or clicks **Confirm**, `mapping_status` is updated to `USER_CONFIRMED`. Subsequent profiling runs detect this status and preserve the user's manual settings unchanged.

---

## 5. Cross-Version Schema Inheritance
When a new `DatasetVersion` is uploaded or generated:
1. `SemanticLayerService.inherit_mappings_for_new_version()` copies existing verified mappings from the previous version to the new version.
2. Columns present in the previous version retain their confirmed business names, semantic types, and formatting.
3. Completely new columns introduced in the new version are profiled and labeled `SYSTEM_INFERRED` or `AI_SUGGESTED`.
4. Historical intelligence records tied to older `DatasetVersion` IDs remain immutable.

