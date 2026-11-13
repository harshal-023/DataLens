# DataLens Formula & Calculated Column Engine

## Security Architecture

The formula engine enforces complete sandboxing and determinism:
- **No `eval()` or `exec()`**: Python code execution is strictly prohibited.
- **Dedicated AST Parser**: Custom tokenizer and recursive descent parser construct an explicit Abstract Syntax Tree.
- **Identifier Whitelisting**: Every referenced column identifier is validated against the active dataset schema before SQL generation.
- **SQL Sanitization**: All column identifiers are strictly escaped with `"` and literals are escaped with `'`.
- **Zero Divide-by-Zero Exceptions**: Division `/` automatically transforms into `({left} / NULLIF({right}, 0))`.

## Syntax Reference

### Arithmetic & Comparison Operators
- `+`, `-`, `*`, `/`, `%`, `^` (power)
- `==` or `=`, `!=` or `<>`, `<`, `<=`, `>`, `>=`
- `AND`, `OR`, `NOT`

### Column References
- Bracket notation: `[Price]`, `[Order Amount]`, `[Sales 2026]`
- Bare identifiers: `price`, `revenue`, `quantity`

### Supported Functions
- **Conditional**: `IF(condition, then_value, else_value)` -> Translates to `CASE WHEN condition THEN then_value ELSE else_value END`
- **Null Safety**: `COALESCE(col1, col2, ...)` or `ISNULL(col, default_val)`
- **String**: `CONCAT(a, b, ...)`, `UPPER(str)`, `LOWER(str)`, `TRIM(str)`, `LENGTH(str)`, `SUBSTRING(str, start, [len])`
- **Math**: `ROUND(num, [decimals])`, `ABS(num)`, `FLOOR(num)`, `CEIL(num)`, `POWER(base, exp)`

### Example Expressions
```excel
[Quantity] * [Unit_Price] * (1 - [Discount_Rate])
```
```excel
IF([Total_Spend] > 5000, 'Enterprise', 'Standard')
```
```excel
CONCAT(UPPER([First_Name]), ' ', UPPER([Last_Name]))
```
```excel
ROUND([Revenue] / [Employees], 2)
```

