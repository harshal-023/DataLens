import time
from pathlib import Path

import pytest

from app.services.dataset_processor import DatasetProcessor


def generate_benchmark_csv(num_rows: int) -> bytes:
    lines = ["id,customer,region,revenue,cost,units,date,active"]
    for i in range(1, num_rows + 1):
        lines.append(
            f"{i},Customer_{i % 50},Region_{i % 4},{100.50 + (i % 500)},{50.25 + (i % 200)},{i % 20},2025-01-{(i % 28) + 1:02d},{'true' if i % 2 == 0 else 'false'}"
        )
    return "\n".join(lines).encode("utf-8")


@pytest.mark.parametrize("row_count", [500, 5000, 10000])
def test_dataset_processing_and_read_performance(tmp_path: Path, row_count: int):
    data = generate_benchmark_csv(row_count)
    file_size_kb = len(data) / 1024

    # 1. Measure Processing & Parquet writing duration
    start_time = time.perf_counter()
    res = DatasetProcessor.process_csv(
        data=data,
        storage_root=tmp_path,
        relative_processed_dir=f"processed/perf_{row_count}",
    )
    process_duration_ms = (time.perf_counter() - start_time) * 1000

    assert res.row_count == row_count
    assert res.column_count == 8
    assert len(res.parquet_parts) >= 1

    # 2. Measure Row Pagination Latency (Page 1)
    start_read = time.perf_counter()
    paged = DatasetProcessor.read_paginated_rows(
        storage_root=tmp_path,
        manifest_key=res.manifest_key,
        offset=0,
        limit=50,
    )
    read_p1_ms = (time.perf_counter() - start_read) * 1000
    assert len(paged["rows"]) == 50

    # 3. Measure Row Pagination Latency (Middle Page)
    mid_offset = row_count // 2
    start_read_mid = time.perf_counter()
    paged_mid = DatasetProcessor.read_paginated_rows(
        storage_root=tmp_path,
        manifest_key=res.manifest_key,
        offset=mid_offset,
        limit=50,
    )
    read_mid_ms = (time.perf_counter() - start_read_mid) * 1000
    assert len(paged_mid["rows"]) == 50

    print(
        f"\n[PERF BENCHMARK - {row_count} rows ({file_size_kb:.1f} KB)]\n"
        f"  - Ingestion, Inferred Schema & Parquet Chunking: {process_duration_ms:.2f}ms\n"
        f"  - Page 1 Retrieval (50 rows): {read_p1_ms:.2f}ms\n"
        f"  - Mid-Dataset Offset Retrieval ({mid_offset}): {read_mid_ms:.2f}ms"
    )

    # Performance assertions: 10,000 rows must process well under 5 seconds
    assert process_duration_ms < 5000
    # Pagination should be instantaneous (< 500ms even with first-call library cold start)
    assert read_p1_ms < 500


@pytest.mark.parametrize("row_count", [500, 5000, 10000])
def test_analytics_and_report_performance(tmp_path: Path, row_count: int):
    """
    Benchmarks cold vs warm DuckDB analytical queries and multi-format document generation.
    """
    from app.services.analytics.engine import AnalyticsEngine
    from app.services.reports.pdf_generator import generate_pdf_report
    from app.services.reports.xlsx_generator import generate_xlsx_report

    data = generate_benchmark_csv(row_count)
    proc = DatasetProcessor.process_csv(
        data=data,
        storage_root=tmp_path,
        relative_processed_dir=f"processed/bench_{row_count}",
    )
    parquet_paths = [tmp_path / p for p in proc.parquet_parts]
    cols_meta = proc.schema_metadata["columns"]

    import uuid

    bench_ds_id = uuid.uuid4()
    # 1. Cold vs Warm Profiling
    t0 = time.perf_counter()
    prof_cold = AnalyticsEngine.compute_profiling(
        parquet_files=parquet_paths,
        columns_meta=cols_meta,
        dataset_id=bench_ds_id,
        version_id="bench-v1",
    )
    cold_prof_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    prof_warm = AnalyticsEngine.compute_profiling(
        parquet_files=parquet_paths,
        columns_meta=cols_meta,
        dataset_id=bench_ds_id,
        version_id="bench-v1",
    )
    warm_prof_ms = (time.perf_counter() - t1) * 1000

    # 2. Aggregation & Time-series
    t2 = time.perf_counter()
    agg = AnalyticsEngine.compute_aggregation(
        parquet_files=parquet_paths,
        group_by_columns=["region"],
        metric_column="revenue",
        aggregation="sum",
        sort_order="desc",
        limit=10,
        filters=None,
        version_id="bench-v1",
    )
    agg_ms = (time.perf_counter() - t2) * 1000

    t3 = time.perf_counter()
    ts = AnalyticsEngine.compute_time_series(
        parquet_files=parquet_paths,
        date_column="date",
        value_column="revenue",
        interval="monthly",
        aggregation="sum",
        filters=None,
        version_id="bench-v1",
    )
    ts_ms = (time.perf_counter() - t3) * 1000

    # 3. Report Generation
    t_pdf = time.perf_counter()
    pdf_bytes = generate_pdf_report(
        title=f"Benchmark Report ({row_count} rows)",
        dataset_name="Benchmark Dataset",
        version_number="v1.0",
        workspace_name="Pro Workspace",
        profile_data=prof_warm.model_dump(),
        agg_data=agg.model_dump(),
    )
    pdf_gen_ms = (time.perf_counter() - t_pdf) * 1000

    t_xlsx = time.perf_counter()
    xlsx_bytes = generate_xlsx_report(
        title=f"Benchmark Workbook ({row_count} rows)",
        dataset_name="Benchmark Dataset",
        version_number="v1.0",
        workspace_name="Pro Workspace",
        profile_data=prof_warm.model_dump(),
        agg_data=agg.model_dump(),
    )
    xlsx_gen_ms = (time.perf_counter() - t_xlsx) * 1000

    print(
        f"\n[ANALYTICS & REPORT BENCHMARK - {row_count} rows]\n"
        f"  - Profiling (Cold): {cold_prof_ms:.2f}ms | (Warm): {warm_prof_ms:.2f}ms\n"
        f"  - Group-by Aggregation: {agg_ms:.2f}ms\n"
        f"  - Time-series Aggregation: {ts_ms:.2f}ms\n"
        f"  - PDF Report Generation ({len(pdf_bytes)} bytes): {pdf_gen_ms:.2f}ms\n"
        f"  - XLSX Workbook Generation ({len(xlsx_bytes)} bytes): {xlsx_gen_ms:.2f}ms"
    )

    assert prof_cold.row_count == row_count
    assert len(agg.items) == 4  # 4 regions
    assert len(ts.points) > 0
    assert len(pdf_bytes) > 1000
    assert len(xlsx_bytes) > 1000
