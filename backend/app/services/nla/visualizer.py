from typing import Any

from app.services.nla.schemas import NLAQueryPlan


class NLAVisualizer:
    """
    Intelligent chart recommendation engine mapping query intent and result data
    characteristics to appropriate visualization configurations.
    """

    @classmethod
    def recommend_chart(
        cls,
        plan: NLAQueryPlan,
        columns: list[str],
        rows: list[dict[str, Any]],
        metric_label: str = "Metric",
    ) -> Any:
        chart_data, _ = cls.recommend_visualization(
            plan=plan,
            result_data={"columns": columns, "rows": rows},
            metric_label=metric_label,
        )
        if chart_data:
            class ChartObj:
                def __init__(self, d: dict[str, Any]):
                    self.__dict__.update(d)
                    self.chart_type = d.get("chart_type")
            return ChartObj(chart_data)
        return None

    @classmethod
    def recommend_visualization(
        cls,
        plan: NLAQueryPlan,
        result_data: dict[str, Any],
        metric_label: str = "Metric",
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """
        Returns: (chart_data, table_data)
        """
        rows = result_data.get("rows", [])
        columns = result_data.get("columns", [])
        if not rows:
            return None, None

        # Build Table Data
        table_data = {
            "columns": [c.replace("_", " ").title() for c in columns],
            "raw_columns": columns,
            "rows": rows,
            "total_rows": len(rows),
        }

        # 1. Scalar (single row, no group by) -> KPI Card only
        if len(rows) == 1 and not plan.group_by_columns and plan.intent not in ("time_series", "trend") and "period" not in columns:
            val = rows[0].get("metric_value", rows[0].get("calculated_metric"))
            chart_data = {
                "chart_type": "kpi",
                "title": f"Total {metric_label}",
                "value": val,
                "formatted_value": f"{val:,.2f}" if isinstance(val, (int, float)) else str(val),
            }
            return chart_data, table_data

        # 2. Time Series -> Line Chart
        if plan.intent in ("time_series", "trend") or "period" in columns or "order_date" in columns:
            date_col = "period" if "period" in columns else ("order_date" if "order_date" in columns else columns[0])
            val_col = "metric_value" if "metric_value" in columns else ("calculated_metric" if "calculated_metric" in columns else columns[-1])
            chart_data = {
                "chart_type": "line",
                "title": f"{metric_label} Trend Over Time",
                "x_key": date_col,
                "y_keys": [val_col],
                "series": rows,
                "labels": [str(r.get(date_col, "")) for r in rows],
                "values": [float(r.get(val_col, 0) or 0) for r in rows],
            }
            return chart_data, table_data

        # 3. Contribution / Share of Total -> Pie / Donut Chart (if <= 7 categories)
        group_col = plan.group_by_columns[0] if plan.group_by_columns else columns[0]
        if plan.intent == "contribution" and len(rows) <= 7:
            chart_data = {
                "chart_type": "pie",
                "title": f"{metric_label} Contribution by {group_col.replace('_', ' ').title()}",
                "x_key": group_col,
                "y_keys": ["share_of_total"],
                "series": rows,
                "labels": [str(r.get(group_col, "")) for r in rows],
                "values": [float(r.get("share_of_total", 0) or 0) for r in rows],
            }
            return chart_data, table_data

        # 4. Discrete Group By / Ranking -> Bar Chart
        chart_data = {
            "chart_type": "bar",
            "title": f"{metric_label} by {group_col.replace('_', ' ').title()}",
            "x_key": group_col,
            "y_keys": ["metric_value"],
            "series": rows[:15],
            "labels": [str(r.get(group_col, "")) for r in rows[:15]],
            "values": [float(r.get("metric_value", 0) or 0) for r in rows[:15]],
        }
        return chart_data, table_data
