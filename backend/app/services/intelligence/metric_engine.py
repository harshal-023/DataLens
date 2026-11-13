import ast
import re
import uuid
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataLensException
from app.core.logging import logger
from app.models.intelligence import MetricDefinition, MetricVersion


class SafeFormulaValidator(ast.NodeVisitor):
    """
    Safely traverses Python AST to validate formula expressions without eval or exec.
    Permits only basic arithmetic (+, -, *, /), constants, column identifiers,
    and safe aggregate functions (SUM, AVG, COUNT, MIN, MAX).
    """

    ALLOWED_NODES = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Call,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.USub,
        ast.UAdd,
        ast.Load,
    )

    ALLOWED_FUNCTIONS = {"SUM", "AVG", "COUNT", "MIN", "MAX", "ROUND", "ABS", "COALESCE"}

    def __init__(self, allowed_columns: set[str] | None = None) -> None:
        self.allowed_columns = {c.lower() for c in (allowed_columns or set())}
        self.referenced_identifiers: set[str] = set()
        self.errors: list[str] = []

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, self.ALLOWED_NODES):
            self.errors.append(f"Forbidden syntax construct '{type(node).__name__}'.")
        super().generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            self.errors.append("Only direct function calls are permitted.")
        else:
            fn_name = node.func.id.upper()
            if fn_name not in self.ALLOWED_FUNCTIONS:
                self.errors.append(
                    f"Unsupported function '{fn_name}'. Allowed: {', '.join(sorted(self.ALLOWED_FUNCTIONS))}."
                )
        for arg in node.args:
            self.visit(arg)

    def visit_Name(self, node: ast.Name) -> None:
        ident = node.id
        self.referenced_identifiers.add(ident)
        if self.allowed_columns and ident.lower() not in self.allowed_columns:
            # Check if it's a function name
            if ident.upper() not in self.ALLOWED_FUNCTIONS:
                self.errors.append(f"Identifier '{ident}' is not a recognized column or metric.")
        self.generic_visit(node)


class MetricIntelligenceEngine:
    """
    Safe mathematical formula compiler and execution engine for business metrics.
    Translates validated formulas into high-performance, division-by-zero protected DuckDB queries.
    """

    @classmethod
    def validate_formula(
        cls, formula: str, available_columns: list[str] | None = None
    ) -> tuple[bool, list[str], list[str]]:
        """
        Validates mathematical expression syntax and safety.
        Returns: (is_valid, referenced_columns, error_messages)
        """
        clean = formula.strip()
        if not clean:
            return False, [], ["Formula expression cannot be empty."]

        # Normalize common notation: e.g. SUM(x) -> SUM(x)
        # Check for disallowed characters
        if re.search(r"[;`'\"]", clean):
            return False, [], ["Quotes, backticks, and semicolons are not permitted in formulas."]

        try:
            tree = ast.parse(clean, mode="eval")
        except SyntaxError as se:
            return False, [], [f"Formula syntax error: {se.msg} at position {se.offset}."]

        validator = SafeFormulaValidator(allowed_columns=set(available_columns) if available_columns else None)
        validator.visit(tree)

        # Filter out function names from referenced identifiers
        real_identifiers = [
            i for i in validator.referenced_identifiers if i.upper() not in SafeFormulaValidator.ALLOWED_FUNCTIONS
        ]

        is_valid = len(validator.errors) == 0
        return is_valid, sorted(real_identifiers), validator.errors

    @classmethod
    def compile_formula_to_sql(cls, formula: str) -> str:
        """
        Compiles an expression like 'Revenue / Total_Orders * 100' or 'SUM(sales) - SUM(cost)'
        into a safe DuckDB expression with division-by-zero protection.
        """
        expr = formula.strip()

        # Replace division: 'a / b' -> 'a / NULLIF(b, 0)'
        def replace_div(match: re.Match[str]) -> str:
            denom = match.group(1).strip()
            return f" / NULLIF({denom}, 0)"

        # Protect bare divisions
        compiled = re.sub(r"/\s*([a-zA-Z0-9_\(\)]+)", replace_div, expr)
        return compiled

    @classmethod
    def calculate_metric_value(
        cls,
        formula: str,
        aggregation: str,
        parquet_files: list[Path],
        source_columns: list[str],
    ) -> dict[str, Any]:
        """
        Executes metric calculation against DuckDB parquet storage.
        """
        is_valid, refs, errors = cls.validate_formula(formula)
        if not is_valid:
            raise DataLensException(f"Invalid metric formula: {'; '.join(errors)}", code="INVALID_FORMULA")

        clean_paths = [str(p.resolve()).replace("\\", "/") for p in parquet_files if p.is_file()]
        if not clean_paths:
            raise DataLensException("Dataset files not found for calculation.", code="FILE_NOT_FOUND")

        source_sql = f"read_parquet([{', '.join(f"'{p}'" for p in clean_paths)}])"
        compiled_sql = cls.compile_formula_to_sql(formula)

        con = duckdb.connect(":memory:")
        try:
            query = f"SELECT ({compiled_sql}) AS metric_val FROM {source_sql}"
            res = con.execute(query).fetchone()
            raw_val = res[0] if res else None
            val = float(raw_val) if raw_val is not None else 0.0

            return {
                "metric_value": round(val, 4),
                "is_null": raw_val is None,
                "formula": formula,
                "compiled_sql": compiled_sql,
            }
        except Exception as ex:
            logger.error("Metric calculation error for '%s': %s", formula, ex)
            raise DataLensException(f"Calculation failed: {ex}", code="CALCULATION_ERROR")
        finally:
            con.close()

    @classmethod
    async def create_metric(
        cls,
        workspace_id: uuid.UUID,
        dataset_id: uuid.UUID | None,
        name: str,
        description: str | None,
        formula: str,
        aggregation: str,
        formatting: str,
        source_columns: list[str],
        owner_id: uuid.UUID | None,
        db: AsyncSession,
    ) -> MetricDefinition:
        """
        Creates and validates a new MetricDefinition with initial MetricVersion.
        """
        is_valid, refs, errors = cls.validate_formula(formula)
        status = "VALID" if is_valid else "INVALID"
        val_error = "; ".join(errors) if errors else None

        metric = MetricDefinition(
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            name=name.strip(),
            description=description,
            formula=formula.strip(),
            source_columns=source_columns or refs,
            aggregation=aggregation.upper(),
            filters=[],
            formatting=formatting.upper(),
            applicable_dimensions=[],
            validation_status=status,
            validation_error=val_error,
            version=1,
            approval_status="APPROVED" if is_valid else "DRAFT",
            owner_id=owner_id,
        )
        db.add(metric)
        await db.flush()

        # Create Version 1 audit
        m_version = MetricVersion(
            metric_id=metric.id,
            version_number=1,
            formula=metric.formula,
            source_columns=metric.source_columns,
            aggregation=metric.aggregation,
            filters=metric.filters,
            formatting=metric.formatting,
            change_summary="Initial metric definition",
            created_by_user_id=owner_id,
        )
        db.add(m_version)
        await db.flush()
        return metric

    @classmethod
    async def update_metric(
        cls,
        metric: MetricDefinition,
        updates: dict[str, Any],
        user_id: uuid.UUID | None,
        change_summary: str | None,
        db: AsyncSession,
    ) -> MetricDefinition:
        """
        Updates a metric, increments version, and records immutable MetricVersion history.
        """
        formula_changed = False
        if "name" in updates:
            metric.name = updates["name"].strip()
        if "description" in updates:
            metric.description = updates["description"]
        if "formatting" in updates:
            metric.formatting = updates["formatting"].upper()
        if "aggregation" in updates:
            metric.aggregation = updates["aggregation"].upper()
        if "approval_status" in updates:
            metric.approval_status = updates["approval_status"].upper()

        if "formula" in updates and updates["formula"].strip() != metric.formula:
            metric.formula = updates["formula"].strip()
            formula_changed = True
            is_valid, refs, errors = cls.validate_formula(metric.formula)
            metric.validation_status = "VALID" if is_valid else "INVALID"
            metric.validation_error = "; ".join(errors) if errors else None
            metric.source_columns = refs

        if formula_changed:
            metric.version += 1
            # Record historical version
            m_ver = MetricVersion(
                metric_id=metric.id,
                version_number=metric.version,
                formula=metric.formula,
                source_columns=metric.source_columns,
                aggregation=metric.aggregation,
                filters=metric.filters,
                formatting=metric.formatting,
                change_summary=change_summary or f"Updated formula to v{metric.version}",
                created_by_user_id=user_id,
            )
            db.add(m_ver)

        await db.flush()
        return metric
