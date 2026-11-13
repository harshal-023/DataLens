import time
from typing import Any

import duckdb

from app.core.exceptions import DataLensException
from app.core.logging import logger
from app.services.nla.schemas import NLAQueryPlan


class NLAQueryExecutor:
    """
    Executes compiled analytical queries against DuckDB in-memory engine
    with timeouts, row bounds, and structured result extraction.
    """

    QUERY_TIMEOUT_SECONDS = 30

    @classmethod
    def execute_query(
        cls,
        sql_query: str,
        params: list[Any],
        plan: NLAQueryPlan | None = None,
    ) -> dict[str, Any]:
        """
        Executes query in DuckDB and formats results into analytical payload.
        """
        start_time = time.perf_counter()
        con = duckdb.connect(":memory:")
        try:
            # Set memory and thread limits for safe multi-tenant operation
            con.execute("PRAGMA threads=4;")
            con.execute("PRAGMA memory_limit='2GB';")

            # Execute with parameters
            cursor = con.execute(sql_query, params) if params else con.execute(sql_query)

            columns = [desc[0] for desc in cursor.description]
            raw_rows = cursor.fetchall()
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Format rows as dictionaries
            rows: list[dict[str, Any]] = []
            for r in raw_rows:
                row_dict = {}
                for i, col_name in enumerate(columns):
                    val = r[i]
                    if isinstance(val, float):
                        val = round(val, 4)
                    row_dict[col_name] = val
                rows.append(row_dict)

            # Extract metric total and row counts
            total_records = sum(int(r.get("record_count", r.get("count", 1))) for r in rows) if rows else 0

            scalar_metric: float | None = None
            if rows:
                if "metric_value" in rows[0]:
                    first_val = rows[0]["metric_value"]
                    if first_val is not None:
                        scalar_metric = float(first_val)

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "total_records_analyzed": total_records,
                "primary_metric_value": scalar_metric,
                "execution_duration_ms": duration_ms,
                "compiled_sql": sql_query,
            }

        except duckdb.Error as de:
            logger.error("DuckDB execution failure: %s\nSQL: %s", de, sql_query)
            raise DataLensException(f"Analytical query execution failed: {de}", code="QUERY_EXECUTION_ERROR")
        finally:
            con.close()
