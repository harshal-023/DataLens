import csv
import io
from typing import Any


def generate_csv_report(
    agg_data: dict[str, Any] | None = None,
    stats_data: dict[str, Any] | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    if agg_data and agg_data.get("items"):
        writer.writerow(["group_key", "value", "row_count", "share_of_total_pct"])
        for item in agg_data["items"]:
            writer.writerow([
                item.get("key"),
                item.get("value"),
                item.get("count"),
                item.get("share_of_total"),
            ])
    elif stats_data and stats_data.get("columns"):
        writer.writerow(["column", "count", "missing_count", "sum", "mean", "median", "min", "max", "std_dev"])
        for col_name, s in stats_data["columns"].items():
            writer.writerow([
                col_name,
                s.get("count"),
                s.get("missing_count"),
                s.get("sum"),
                s.get("mean"),
                s.get("median"),
                s.get("min"),
                s.get("max"),
                s.get("standard_deviation"),
            ])
    elif raw_rows and len(raw_rows) > 0:
        headers = list(raw_rows[0].keys())
        writer.writerow(headers)
        for r in raw_rows:
            writer.writerow([r.get(h) for h in headers])
    else:
        writer.writerow(["metric", "value"])
        writer.writerow(["status", "no data"])

    return buffer.getvalue().encode("utf-8")

