import re
from pathlib import Path
from typing import Any

import duckdb

from app.core.exceptions import DataLensException
from app.core.logging import logger


class DatasetIntelligenceProfiler:
    """
    Comprehensive, bounded DuckDB-powered intelligence profiler for immutable Parquet datasets.
    Extracts physical and logical types, distributions, outliers, candidate PKs/FKs,
    dimensions, measures, data quality warnings, and semantic classifications.
    """

    SEMANTIC_KEYWORDS: dict[str, list[str]] = {
        "currency": [
            "revenue", "price", "cost", "amount", "sales", "salary", "fee", "mrp",
            "total", "subtotal", "tax", "discount_amount", "spend", "budget", "inr", "usd", "eur"
        ],
        "percentage": [
            "percent", "pct", "rate", "ratio", "margin", "discount_pct", "growth_rate", "churn_rate"
        ],
        "quantity": [
            "qty", "quantity", "units", "items", "volume", "count", "inventory", "stock", "headcount"
        ],
        "customer_identifier": [
            "customer_id", "cust_id", "client_id", "user_id", "buyer_id", "member_id", "shopper_id"
        ],
        "product_identifier": [
            "product_id", "prod_id", "item_id", "sku", "barcode", "upc", "asin", "part_number"
        ],
        "transaction_identifier": [
            "order_id", "transaction_id", "txn_id", "invoice_id", "receipt_id", "payment_id", "shipment_id"
        ],
        "email": ["email", "e_mail", "mail_address"],
        "phone": ["phone", "mobile", "tel", "cell", "contact_no", "telephone"],
        "geographic_region": [
            "country", "state", "city", "zip", "zipcode", "postal", "region", "province",
            "county", "territory", "latitude", "longitude", "lat", "lon"
        ],
        "address": ["address", "street", "street_address", "billing_address", "shipping_address"],
        "status": ["status", "state", "stage", "order_status", "payment_status", "condition"],
        "category": ["category", "dept", "department", "segment", "type", "sub_category", "genre", "class"],
        "date": ["date", "day", "month", "year", "quarter", "dob", "birth_date", "order_date", "ship_date"],
        "timestamp": ["timestamp", "created_at", "updated_at", "deleted_at", "logged_at", "time"],
    }

    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    PHONE_REGEX = re.compile(r"^\+?[0-9\s\-\(\)]{7,20}$")
    DATE_REGEX = re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}")

    @classmethod
    def _sanitize_identifier(cls, name: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", name):
            raise DataLensException(f"Invalid column identifier: '{name}'.", code="INVALID_COLUMN")
        return f'"{name}"'

    @classmethod
    def _get_parquet_source_sql(cls, parquet_files: list[Path]) -> str:
        if not parquet_files:
            raise DataLensException("Dataset has no Parquet data parts.", code="NOT_FOUND")
        clean_paths = [str(p.resolve()).replace("\\", "/") for p in parquet_files if p.is_file()]
        if not clean_paths:
            raise DataLensException("Parquet data files not found on disk.", code="FILE_NOT_FOUND")
        escaped_paths = ", ".join(f"'{p}'" for p in clean_paths)
        return f"read_parquet([{escaped_paths}])"

    @classmethod
    def profile_parquet_dataset(
        cls, parquet_files: list[Path]
    ) -> dict[str, Any]:
        """
        Runs bounded statistical profiling queries via DuckDB over the Parquet files.
        """
        source_sql = cls._get_parquet_source_sql(parquet_files)
        con = duckdb.connect(":memory:")
        try:
            # 1. Total row count and schema
            row_count_res = con.execute(f"SELECT COUNT(*) FROM {source_sql}").fetchone()
            total_rows = int(row_count_res[0]) if row_count_res else 0
            if total_rows == 0:
                return {
                    "total_rows": 0,
                    "column_count": 0,
                    "duplicate_rows": 0,
                    "quality_score": 100,
                    "columns": {},
                    "warnings": [{"severity": "HIGH", "message": "Dataset contains 0 rows"}],
                    "candidate_pks": [],
                    "candidate_fks": [],
                    "candidate_dimensions": [],
                    "candidate_measures": [],
                }

            # 2. Duplicate rows estimation (bounded hash distinct vs total)
            try:
                dup_res = con.execute(
                    f"SELECT COUNT(*) - COUNT(DISTINCT hash(*)) FROM {source_sql}"
                ).fetchone()
                duplicate_rows = max(0, int(dup_res[0])) if dup_res else 0
            except Exception:
                duplicate_rows = 0

            # 3. Column schema & physical types
            describe_res = con.execute(f"DESCRIBE SELECT * FROM {source_sql} LIMIT 0").fetchall()
            # row: (column_name, column_type, null, key, default, extra)
            columns_info: dict[str, str] = {row[0]: row[1] for row in describe_res}

            column_profiles: dict[str, Any] = {}
            candidate_pks: list[str] = []
            candidate_fks: list[str] = []
            candidate_dimensions: list[str] = []
            candidate_measures: list[str] = []
            all_warnings: list[dict[str, Any]] = []

            if duplicate_rows > 0:
                all_warnings.append({
                    "severity": "MEDIUM",
                    "column": None,
                    "type": "DUPLICATE_ROWS",
                    "message": f"Found {duplicate_rows} duplicate rows ({duplicate_rows / total_rows * 100:.1f}%).",
                })

            for col_name, physical_type in columns_info.items():
                safe_col = cls._sanitize_identifier(col_name)
                upper_phys = physical_type.upper()

                # Basic counts: total, nulls, distinct
                try:
                    stats_query = f"""
                        SELECT
                            COUNT({safe_col}) AS non_null_count,
                            COUNT(*) - COUNT({safe_col}) AS null_count,
                            COUNT(DISTINCT {safe_col}) AS distinct_count
                        FROM {source_sql}
                    """
                    row = con.execute(stats_query).fetchone()
                    non_null_count = int(row[0]) if row else 0
                    null_count = int(row[1]) if row else 0
                    distinct_count = int(row[2]) if row else 0
                except Exception as ex:
                    logger.warning("Failed base stats for %s: %s", col_name, ex)
                    non_null_count, null_count, distinct_count = total_rows, 0, 0

                null_pct = round((null_count / total_rows) * 100, 2)
                uniqueness_pct = round((distinct_count / total_rows) * 100, 2) if total_rows > 0 else 0

                is_numeric = any(t in upper_phys for t in ("INT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"))
                is_temporal = any(t in upper_phys for t in ("DATE", "TIME", "TIMESTAMP"))
                is_boolean = "BOOL" in upper_phys

                # Infer logical type
                logical_type = "string"
                if is_boolean:
                    logical_type = "boolean"
                elif is_temporal:
                    logical_type = "datetime" if "TIMESTAMP" in upper_phys or "TIME" in upper_phys else "date"
                elif is_numeric:
                    logical_type = "integer" if any(t in upper_phys for t in ("INT", "BIGINT", "SMALLINT")) else "float"

                numeric_stats: dict[str, Any] = {}
                temporal_stats: dict[str, Any] = {}
                top_categories: list[dict[str, Any]] = []
                outlier_count = 0

                # Numeric profiling: min, max, avg, stddev, quantiles
                if is_numeric and non_null_count > 0:
                    try:
                        num_q = f"""
                            SELECT
                                MIN({safe_col}),
                                MAX({safe_col}),
                                AVG({safe_col}),
                                STDDEV_SAMP({safe_col}),
                                QUANTILE_CONT({safe_col}, 0.25),
                                QUANTILE_CONT({safe_col}, 0.50),
                                QUANTILE_CONT({safe_col}, 0.75)
                            FROM {source_sql}
                            WHERE {safe_col} IS NOT NULL
                        """
                        nr = con.execute(num_q).fetchone()
                        if nr:
                            min_val = float(nr[0]) if nr[0] is not None else None
                            max_val = float(nr[1]) if nr[1] is not None else None
                            mean_val = float(nr[2]) if nr[2] is not None else None
                            stddev_val = float(nr[3]) if nr[3] is not None else 0.0
                            q1 = float(nr[4]) if nr[4] is not None else None
                            q2 = float(nr[5]) if nr[5] is not None else None
                            q3 = float(nr[6]) if nr[6] is not None else None
                            iqr = (q3 - q1) if (q1 is not None and q3 is not None) else None

                            numeric_stats = {
                                "min": min_val,
                                "max": max_val,
                                "mean": round(mean_val, 2) if mean_val is not None else None,
                                "stddev": round(stddev_val, 2) if stddev_val is not None else 0.0,
                                "q1": q1,
                                "median": q2,
                                "q3": q3,
                                "iqr": iqr,
                            }

                            # Outlier check using IQR (1.5 * IQR)
                            if iqr and iqr > 0 and q1 is not None and q3 is not None:
                                lower_bound = q1 - 1.5 * iqr
                                upper_bound = q3 + 1.5 * iqr
                                out_q = f"""
                                    SELECT COUNT(*) FROM {source_sql}
                                    WHERE {safe_col} < {lower_bound} OR {safe_col} > {upper_bound}
                                """
                                out_r = con.execute(out_q).fetchone()
                                outlier_count = int(out_r[0]) if out_r else 0
                    except Exception as ex:
                        logger.warning("Numeric stats calculation failed for %s: %s", col_name, ex)

                # Temporal profiling: min_date, max_date
                if is_temporal and non_null_count > 0:
                    try:
                        temp_q = f"""
                            SELECT MIN({safe_col}), MAX({safe_col})
                            FROM {source_sql}
                            WHERE {safe_col} IS NOT NULL
                        """
                        tr = con.execute(temp_q).fetchone()
                        if tr:
                            temporal_stats = {
                                "min_date": str(tr[0]) if tr[0] else None,
                                "max_date": str(tr[1]) if tr[1] else None,
                            }
                    except Exception as ex:
                        logger.warning("Temporal stats calculation failed for %s: %s", col_name, ex)

                # Categorical / sample values: top 10 frequent
                sample_values: list[str] = []
                try:
                    top_q = f"""
                        SELECT CAST({safe_col} AS VARCHAR) AS val, COUNT(*) AS cnt
                        FROM {source_sql}
                        WHERE {safe_col} IS NOT NULL
                        GROUP BY 1
                        ORDER BY cnt DESC
                        LIMIT 10
                    """
                    cat_rows = con.execute(top_q).fetchall()
                    for r in cat_rows:
                        val_str = str(r[0])[:100]
                        sample_values.append(val_str)
                        top_categories.append({
                            "value": val_str,
                            "count": int(r[1]),
                            "share_pct": round((int(r[1]) / total_rows) * 100, 2),
                        })
                except Exception as ex:
                    logger.warning("Category sample query failed for %s: %s", col_name, ex)

                # Multi-Signal Semantic Classification
                semantic_type, confidence = cls.infer_semantic_type(
                    col_name=col_name,
                    physical_type=physical_type,
                    logical_type=logical_type,
                    distinct_count=distinct_count,
                    total_rows=total_rows,
                    sample_values=sample_values,
                    numeric_stats=numeric_stats,
                )

                # Primary Key Candidate:
                # 100% uniqueness, 0 nulls, not float, has some identifier pattern or numeric/uuid type
                is_pk = False
                if null_count == 0 and distinct_count == total_rows and total_rows > 0:
                    if logical_type in ("integer", "string") and not is_boolean:
                        is_pk = True
                        candidate_pks.append(col_name)

                # Foreign Key Candidate:
                # Name ends with _id, _key, _code, or matches known entity patterns, not PK
                is_fk = False
                lower_name = col_name.lower()
                if not is_pk and (
                    lower_name.endswith(("_id", "_key", "_code", "_fk"))
                    or "identifier" in semantic_type
                ):
                    is_fk = True
                    candidate_fks.append(col_name)

                # Candidate Measure vs Dimension
                is_measure = False
                is_dimension = False
                if is_numeric and not is_pk and not is_fk and "identifier" not in semantic_type:
                    # Continuous values or currency/percentages are measures
                    if distinct_count > 10 or semantic_type in ("currency", "percentage", "quantity"):
                        is_measure = True
                        candidate_measures.append(col_name)
                    else:
                        is_dimension = True
                        candidate_dimensions.append(col_name)
                elif is_temporal or is_boolean or distinct_count < total_rows or is_pk or is_fk:
                    is_dimension = True
                    candidate_dimensions.append(col_name)

                # Suggested Aggregation
                agg_method = "NONE"
                if is_measure:
                    agg_method = "AVG" if semantic_type == "percentage" else "SUM"
                elif is_pk or is_fk:
                    agg_method = "COUNT_DISTINCT"
                elif is_dimension:
                    agg_method = "COUNT"

                # Suggested Formatting
                format_string = None
                if semantic_type == "currency":
                    format_string = "INR" if "inr" in lower_name else "USD"
                elif semantic_type == "percentage":
                    format_string = "PERCENT"
                elif is_numeric and logical_type == "integer":
                    format_string = "INTEGER"
                elif is_numeric:
                    format_string = "DECIMAL"

                # Quality warnings for column
                col_warnings: list[str] = []
                if null_pct > 20:
                    col_warnings.append(f"High missing rate: {null_pct}% nulls.")
                    all_warnings.append({
                        "severity": "HIGH" if null_pct > 50 else "MEDIUM",
                        "column": col_name,
                        "type": "HIGH_NULLS",
                        "message": f"Column '{col_name}' has {null_pct}% missing values.",
                    })
                if distinct_count == 1 and total_rows > 1:
                    col_warnings.append("Constant column (only 1 distinct value).")
                    all_warnings.append({
                        "severity": "LOW",
                        "column": col_name,
                        "type": "CONSTANT_COLUMN",
                        "message": f"Column '{col_name}' has only 1 distinct value.",
                    })
                if semantic_type in ("currency", "quantity") and numeric_stats.get("min", 0) < 0:
                    col_warnings.append("Contains negative values for positive measure.")
                    all_warnings.append({
                        "severity": "MEDIUM",
                        "column": col_name,
                        "type": "SUSPICIOUS_NEGATIVE",
                        "message": f"Column '{col_name}' ({semantic_type}) contains negative values.",
                    })
                if outlier_count > 0:
                    col_warnings.append(f"Detected {outlier_count} statistical outliers.")
                    all_warnings.append({
                        "severity": "LOW",
                        "column": col_name,
                        "type": "OUTLIERS",
                        "message": f"Column '{col_name}' has {outlier_count} statistical outliers.",
                    })

                # Human-friendly Business Name suggestion
                business_name = cls.suggest_business_name(col_name)

                column_profiles[col_name] = {
                    "column_name": col_name,
                    "business_name": business_name,
                    "physical_type": physical_type,
                    "logical_type": logical_type,
                    "semantic_type": semantic_type,
                    "confidence_score": confidence,
                    "total_count": total_rows,
                    "null_count": null_count,
                    "null_pct": null_pct,
                    "distinct_count": distinct_count,
                    "uniqueness_pct": uniqueness_pct,
                    "is_primary_key": is_pk,
                    "is_foreign_key": is_fk,
                    "is_dimension": is_dimension,
                    "is_measure": is_measure,
                    "aggregation_method": agg_method,
                    "format_string": format_string,
                    "sample_values": sample_values[:5],
                    "top_categories": top_categories,
                    "numeric_stats": numeric_stats,
                    "temporal_stats": temporal_stats,
                    "outliers_count": outlier_count,
                    "warnings": col_warnings,
                }

            # Overall Quality Score (100 - penalties)
            penalty = 0
            for w in all_warnings:
                sev = w.get("severity", "LOW")
                if sev == "HIGH":
                    penalty += 15
                elif sev == "MEDIUM":
                    penalty += 7
                else:
                    penalty += 2
            quality_score = max(10, 100 - penalty)

            return {
                "total_rows": total_rows,
                "column_count": len(columns_info),
                "duplicate_rows": duplicate_rows,
                "quality_score": quality_score,
                "columns": column_profiles,
                "warnings": all_warnings,
                "candidate_pks": candidate_pks,
                "candidate_fks": candidate_fks,
                "candidate_dimensions": candidate_dimensions,
                "candidate_measures": candidate_measures,
            }

        finally:
            con.close()

    @classmethod
    def suggest_business_name(cls, col_name: str) -> str:
        """
        Transforms snake_case, camelCase, or abbreviated column names into professional business titles.
        Example: 'cust_order_amt' -> 'Customer Order Amount'
        """
        # Common domain abbreviations
        acronyms = {
            "id": "ID",
            "amt": "Amount",
            "qty": "Quantity",
            "cust": "Customer",
            "prod": "Product",
            "cat": "Category",
            "num": "Number",
            "pct": "Percentage",
            "rev": "Revenue",
            "desc": "Description",
            "dt": "Date",
            "ts": "Timestamp",
            "avg": "Average",
            "tot": "Total",
            "diff": "Difference",
            "addr": "Address",
            "yr": "Year",
            "mo": "Month",
            "sku": "SKU",
        }

        # Normalize camelCase to snake_case
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", col_name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        tokens = re.split(r"[_\s\-]+", s2)
        expanded: list[str] = []
        for t in tokens:
            if not t:
                continue
            if t in acronyms:
                expanded.append(acronyms[t])
            else:
                expanded.append(t.capitalize())

        return " ".join(expanded) if expanded else col_name.title()

    @classmethod
    def infer_semantic_type(
        cls,
        col_name: str,
        physical_type: str,
        logical_type: str,
        distinct_count: int,
        total_rows: int,
        sample_values: list[str],
        numeric_stats: dict[str, Any],
    ) -> tuple[str, float]:
        """
        Multi-signal semantic classification using column name tokens, data types,
        statistical characteristics, and sample content.
        Returns: (semantic_type, confidence_score)
        """
        lower_name = col_name.lower().replace("-", "_").strip()
        tokens = set(re.split(r"[_\s]+", lower_name))

        # 1. Date and Timestamp check
        if (
            logical_type in ("date", "datetime")
            or any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["date"])
            or any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["timestamp"])
            or (sample_values and all(cls.DATE_REGEX.match(v) for v in sample_values[:3]))
        ):
            if logical_type == "datetime" or any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["timestamp"]):
                return "timestamp", 0.95
            return "date", 0.95

        # 2. Email check
        if any(k in tokens for k in cls.SEMANTIC_KEYWORDS["email"]):
            return "email", 0.95
        if sample_values and any(cls.EMAIL_REGEX.match(v) for v in sample_values):
            return "email", 0.98

        # 3. Phone check
        if any(k in tokens for k in cls.SEMANTIC_KEYWORDS["phone"]):
            return "phone", 0.95
        if sample_values and len(sample_values) >= 2 and all(cls.PHONE_REGEX.match(v) for v in sample_values[:3]):
            return "phone", 0.85

        # 3. Customer Identifier
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["customer_identifier"]):
            return "customer_identifier", 0.95

        # 4. Product Identifier
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["product_identifier"]):
            return "product_identifier", 0.95

        # 5. Transaction Identifier
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["transaction_identifier"]):
            return "transaction_identifier", 0.95

        # 6. Currency
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["currency"]):
            if logical_type in ("float", "integer"):
                return "currency", 0.95
            return "currency", 0.70

        # 7. Percentage
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["percentage"]):
            return "percentage", 0.90
        # Check value bounds (between 0 and 1 or 0 and 100)
        if (
            logical_type == "float"
            and numeric_stats.get("min") is not None
            and numeric_stats.get("max") is not None
        ):
            mn, mx = numeric_stats["min"], numeric_stats["max"]
            if mn >= 0 and mx <= 1.0 and any(t in lower_name for t in ("rate", "ratio", "pct", "share", "margin")):
                return "percentage", 0.92

        # 8. Quantity
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["quantity"]):
            if logical_type in ("integer", "float"):
                return "quantity", 0.90

        # 9. Date and Timestamp
        if logical_type in ("date", "datetime") or any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["timestamp"]):
            return "timestamp", 0.95
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["date"]):
            return "date", 0.95

        # 10. Geographic Region
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["geographic_region"]):
            return "geographic_region", 0.88

        # 11. Address
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["address"]):
            return "address", 0.90

        # 12. Status
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["status"]):
            return "status", 0.90

        # 13. Category
        if any(k in lower_name for k in cls.SEMANTIC_KEYWORDS["category"]) or (
            logical_type == "string" and 1 < distinct_count <= 25 and total_rows > 50
        ):
            return "category", 0.80

        # 14. Fallbacks by logical type
        if logical_type in ("integer", "float"):
            return "numeric", 0.75
        if logical_type == "boolean":
            return "boolean", 0.99

        return "text", 0.70
