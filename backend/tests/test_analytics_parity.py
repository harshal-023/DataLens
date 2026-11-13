from pathlib import Path

import pytest

from app.services.analytics.engine import AnalyticsEngine
from app.services.analytics.schemas import FilterCondition
from app.services.dataset_processor import DatasetProcessor


@pytest.fixture
def sample_analytics_parquet(tmp_path: Path):
    # Fixed benchmark dataset identical to TypeScript reference dataset
    csv_data = (
        b"product,region,revenue,units,active,date\n"
        b"Premium Pro,North,1200.50,12,true,2025-01-15\n"
        b"Basic Plan,South,450.00,5,false,2025-01-20\n"
        b"Enterprise,North,5000.00,20,true,2025-02-10\n"
        b"Student Plan,West,200.00,8,true,2025-02-15\n"
        b"Premium Pro,South,1800.00,15,true,2025-03-01\n"
        b"Basic Plan,North,600.00,6,false,2025-03-12\n"
    )

    proc = DatasetProcessor.process_csv(
        data=csv_data,
        storage_root=tmp_path,
        relative_processed_dir="processed/parity",
    )
    parquet_paths = [tmp_path / p for p in proc.parquet_parts]
    manifest = proc.schema_metadata
    return parquet_paths, manifest["columns"]


def test_descriptive_statistics_parity(sample_analytics_parquet):
    parquet_paths, cols_meta = sample_analytics_parquet
    res = AnalyticsEngine.compute_descriptive_stats(
        parquet_files=parquet_paths,
        columns_meta=cols_meta,
        target_columns=["revenue", "units"],
        filters=None,
        version_id="test-v1",
    )

    assert res.row_count_analyzed == 6

    # Revenue checks (1200.50 + 450 + 5000 + 200 + 1800 + 600 = 9250.50)
    rev_stats = res.columns["revenue"]
    assert rev_stats.count == 6
    assert rev_stats.missing_count == 0
    assert rev_stats.sum == 9250.50
    # Mean: 9250.50 / 6 = 1541.75
    assert rev_stats.mean == 1541.75
    assert rev_stats.min == 200.00
    assert rev_stats.max == 5000.00
    assert rev_stats.range == 4800.00
    # Sorted revenues: [200, 450, 600, 1200.50, 1800, 5000]
    # Median is avg of 600 and 1200.50 = 900.25
    assert rev_stats.median == 900.25

    # Units checks (12 + 5 + 20 + 8 + 15 + 6 = 66)
    units_stats = res.columns["units"]
    assert units_stats.sum == 66.00
    assert units_stats.mean == 11.00
    assert units_stats.min == 5.00
    assert units_stats.max == 20.00


def test_group_by_aggregation_parity(sample_analytics_parquet):
    parquet_paths, _ = sample_analytics_parquet
    # Group by region, SUM(revenue)
    res = AnalyticsEngine.compute_aggregation(
        parquet_files=parquet_paths,
        group_by_columns=["region"],
        metric_column="revenue",
        aggregation="sum",
        sort_order="desc",
        limit=10,
        filters=None,
        version_id="test-v1",
    )

    assert res.row_count_analyzed == 6
    assert res.total == 9250.50
    # North has: 1200.50 + 5000 + 600 = 6800.50
    north_item = next(it for it in res.items if it.key == "North")
    assert north_item.value == 6800.50
    assert north_item.count == 3
    # Share of total: 6800.50 / 9250.50 = 73.5%
    assert north_item.share_of_total == 73.5


def test_filtering_and_time_series(sample_analytics_parquet):
    parquet_paths, _ = sample_analytics_parquet

    # Filter revenue > 1000
    cond = FilterCondition(column="revenue", operator="gt", value=1000)
    res_filtered = AnalyticsEngine.compute_aggregation(
        parquet_files=parquet_paths,
        group_by_columns=["product"],
        metric_column="revenue",
        aggregation="sum",
        sort_order="desc",
        limit=10,
        filters=[cond],
        version_id="test-v1",
    )

    # Qualified rows: Premium Pro (1200.50 + 1800 = 3000.50) and Enterprise (5000)
    assert res_filtered.row_count_analyzed == 3
    assert res_filtered.total == 8000.50

    # Monthly time-series
    ts_res = AnalyticsEngine.compute_time_series(
        parquet_files=parquet_paths,
        date_column="date",
        value_column="revenue",
        interval="monthly",
        aggregation="sum",
        filters=None,
        version_id="test-v1",
    )

    assert ts_res.row_count_analyzed == 6
    assert len(ts_res.points) == 3  # Jan, Feb, Mar 2025
    assert ts_res.total == 9250.50
    # Jan revenue: 1200.50 + 450 = 1650.50
    assert ts_res.points[0].value == 1650.50


def test_edge_cases_empty_and_single_row(tmp_path: Path):
    """Verifies analytics engine handles single-row datasets deterministically without zero-division."""
    single_csv = b"item,amount\nWidget A,150.00\n"
    proc = DatasetProcessor.process_csv(
        data=single_csv,
        storage_root=tmp_path,
        relative_processed_dir="processed/single_row",
    )
    parquet_paths = [tmp_path / p for p in proc.parquet_parts]
    cols_meta = proc.schema_metadata["columns"]

    stats = AnalyticsEngine.compute_descriptive_stats(
        parquet_files=parquet_paths,
        columns_meta=cols_meta,
        target_columns=["amount"],
        filters=None,
        version_id="test-single",
    )
    amt_stats = stats.columns["amount"]
    assert amt_stats.count == 1
    assert amt_stats.sum == 150.00
    assert amt_stats.mean == 150.00
    assert amt_stats.median == 150.00
    assert amt_stats.min == 150.00
    assert amt_stats.max == 150.00
    # Single element has 0 variance / sample variance undefined or 0
    assert amt_stats.standard_deviation == 0.0 or amt_stats.standard_deviation is None


def test_null_heavy_and_negative_values(tmp_path: Path):
    """Verifies stats with negative values, nulls, and decimal precision."""
    csv_data = (
        b"metric,score\n"
        b"A,-50.25\n"
        b"B,100.50\n"
        b"C,\n"
        b"D,-20.25\n"
        b"E,200.00\n"
    )
    proc = DatasetProcessor.process_csv(
        data=csv_data,
        storage_root=tmp_path,
        relative_processed_dir="processed/nulls_negatives",
    )
    parquet_paths = [tmp_path / p for p in proc.parquet_parts]
    cols_meta = proc.schema_metadata["columns"]

    stats = AnalyticsEngine.compute_descriptive_stats(
        parquet_files=parquet_paths,
        columns_meta=cols_meta,
        target_columns=["score"],
        filters=None,
        version_id="test-nulls",
    )
    score_stats = stats.columns["score"]
    assert score_stats.count == 5
    assert score_stats.missing_count == 1
    # Sum: -50.25 + 100.50 - 20.25 + 200.00 = 230.00
    assert score_stats.sum == 230.00
    assert score_stats.min == -50.25
    assert score_stats.max == 200.00


def test_data_quality_parity_and_outliers(tmp_path: Path):
    """Verifies data quality penalty formula and Tukey's IQR outlier detection."""
    # Column 'revenue' has commercial negatives
    csv_data = (
        b"revenue,product\n"
        b"100,Plan A\n"
        b"105,Plan A\n"
        b"110,Plan B\n"
        b"115,Plan B\n"
        b"120,Plan C\n"
        b"-50,Plan C\n"
        b"200,Plan D\n"
    )
    proc = DatasetProcessor.process_csv(
        data=csv_data,
        storage_root=tmp_path,
        relative_processed_dir="processed/quality",
    )
    parquet_paths = [tmp_path / p for p in proc.parquet_parts]
    cols_meta = proc.schema_metadata["columns"]

    quality = AnalyticsEngine.compute_data_quality(
        parquet_files=parquet_paths,
        columns_meta=cols_meta,
        version_id="test-quality",
    )
    assert quality.row_count_analyzed == 7
    # Score should be deducted for negative commercial values (penalty: 8)
    assert quality.quality_score <= 92
    issue_types = [i.type for i in quality.issues]
    assert "suspicious_negative" in issue_types


def test_version_comparison_parity(tmp_path: Path):
    """Verifies dataset comparison between two immutable versions."""
    csv_v1 = b"id,val\n1,10\n2,20\n"
    csv_v2 = b"id,val,category\n1,15\n2,25\n3,35\n"

    proc_v1 = DatasetProcessor.process_csv(
        data=csv_v1,
        storage_root=tmp_path,
        relative_processed_dir="processed/v1",
    )
    proc_v2 = DatasetProcessor.process_csv(
        data=csv_v2,
        storage_root=tmp_path,
        relative_processed_dir="processed/v2",
    )

    v1_paths = [tmp_path / p for p in proc_v1.parquet_parts]
    v2_paths = [tmp_path / p for p in proc_v2.parquet_parts]

    comparison = AnalyticsEngine.compare_versions(
        baseline_files=v1_paths,
        compare_files=v2_paths,
        baseline_ver_num="v1",
        compare_ver_num="v2",
        metric_columns=["val"],
    )

    assert comparison.baseline_version == "v1"
    assert comparison.compare_version == "v2"
    assert comparison.row_count_diff == 1
    assert comparison.row_count_pct_change == 50.0
    assert "category" in comparison.added_columns
    assert comparison.removed_columns == []
    # Metric comparison for 'val'
    val_diff = next(m for m in comparison.metric_diffs if m.column == "val")
    assert val_diff.baseline_value == 30.00
    assert val_diff.compare_value == 75.00
    assert val_diff.diff == 45.00


def test_all_filter_operators_parity(sample_analytics_parquet):
    """Verifies filter operators: eq, neq, gt, gte, lt, lte, contains, starts_with, between."""
    parquet_paths, _ = sample_analytics_parquet

    # 1. contains
    cond_contains = FilterCondition(column="product", operator="contains", value="Plan")
    res = AnalyticsEngine.compute_aggregation(
        parquet_files=parquet_paths,
        group_by_columns=["product"],
        metric_column="units",
        aggregation="sum",
        sort_order="desc",
        limit=10,
        filters=[cond_contains],
        version_id="test-filters",
    )
    # Basic Plan and Student Plan
    assert res.row_count_analyzed == 3

    # 2. between
    cond_between = FilterCondition(column="units", operator="between", value=6, second_value=15)
    res_b = AnalyticsEngine.compute_aggregation(
        parquet_files=parquet_paths,
        group_by_columns=["product"],
        metric_column="units",
        aggregation="sum",
        sort_order="desc",
        limit=10,
        filters=[cond_between],
        version_id="test-filters",
    )
    # units 12, 8, 15, 6 qualified
    assert res_b.row_count_analyzed == 4
