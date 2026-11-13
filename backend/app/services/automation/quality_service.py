"""Data quality validation service for dataset materialization and pipeline steps."""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.automation import DataQualityRuleConfig, DataQualityValidationResult

logger = logging.getLogger("datalens.automation.quality")


class DataQualityService:
    """Evaluates configurable data quality gates against datasets."""

    @classmethod
    def validate_dataset_records(
        cls,
        rows: list[dict[str, Any]],
        columns: list[str],
        config: DataQualityRuleConfig,
    ) -> DataQualityValidationResult:
        """Validate list of row dictionaries against data quality rules."""
        issues: list[str] = []
        total_rows = len(rows)
        total_cols = len(columns)

        # 1. Row count bounds
        if total_rows < config.min_row_count:
            issues.append(f"Row count {total_rows} is below minimum threshold of {config.min_row_count}")

        if config.max_row_count is not None and total_rows > config.max_row_count:
            issues.append(f"Row count {total_rows} exceeds maximum threshold of {config.max_row_count}")

        # 2. Required columns check
        missing_columns = [col for col in config.required_columns if col not in columns]
        if missing_columns:
            issues.append(f"Missing required columns: {', '.join(missing_columns)}")

        # 3. Expected types check
        if rows and config.expected_column_types:
            sample_row = rows[0]
            for col, expected_type in config.expected_column_types.items():
                if col in sample_row and sample_row[col] is not None:
                    val = sample_row[col]
                    exp = expected_type.lower()
                    if exp in ("int", "integer") and not isinstance(val, int):
                        issues.append(f"Column '{col}' expected type Integer, found {type(val).__name__}")
                    elif exp in ("float", "double", "decimal", "numeric") and not isinstance(val, (float, int)):
                        issues.append(f"Column '{col}' expected type Float, found {type(val).__name__}")
                    elif exp in ("str", "string", "varchar") and not isinstance(val, str):
                        issues.append(f"Column '{col}' expected type String, found {type(val).__name__}")
                    elif exp in ("bool", "boolean") and not isinstance(val, bool):
                        issues.append(f"Column '{col}' expected type Boolean, found {type(val).__name__}")

        # 4. Null percentage check
        null_counts: dict[str, int] = {c: 0 for c in columns}
        if total_rows > 0:
            for row in rows:
                for col in columns:
                    val = row.get(col)
                    if val is None or val == "":
                        null_counts[col] += 1

        null_percentages: dict[str, float] = {}
        for col, count in null_counts.items():
            pct = (count / total_rows * 100.0) if total_rows > 0 else 0.0
            null_percentages[col] = round(pct, 2)
            if pct > config.max_null_pct:
                issues.append(f"Column '{col}' null rate {pct:.1f}% exceeds max threshold {config.max_null_pct}%")

        # 5. Duplicate row percentage check
        duplicate_count = 0
        if total_rows > 1:
            seen_signatures: set[str] = set()
            for row in rows:
                sig = repr(sorted([(k, str(v)) for k, v in row.items() if not k.startswith("_")]))
                if sig in seen_signatures:
                    duplicate_count += 1
                else:
                    seen_signatures.add(sig)

            dup_pct = (duplicate_count / total_rows * 100.0)
            if dup_pct > config.max_duplicate_pct:
                issues.append(f"Duplicate row rate {dup_pct:.1f}% exceeds max threshold {config.max_duplicate_pct}%")

        passed = len(issues) == 0

        return DataQualityValidationResult(
            passed=passed,
            action=config.on_failure,
            issues=issues,
            row_count=total_rows,
            column_count=total_cols,
            null_percentages=null_percentages,
            duplicate_rows_detected=duplicate_count,
        )

