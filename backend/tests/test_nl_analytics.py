import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.core.exceptions import DataLensException
from app.models.intelligence import (
    ColumnSemanticMapping,
    MetricDefinition,
)
from app.services.nla.compiler import NLASafeQueryCompiler
from app.services.nla.executor import NLAQueryExecutor
from app.services.nla.planner import NLAQueryPlanner
from app.services.nla.schemas import FilterItem, NLAQueryPlan
from app.services.nla.verifier import NLAEvidenceVerifier
from app.services.nla.visualizer import NLAVisualizer


@pytest.fixture
def sample_sales_parquet(tmp_path: Path) -> Path:
    """Creates a temporary Parquet file simulating retail sales orders."""
    data = {
        "order_id": [f"ORD-{i:04d}" for i in range(1, 101)],
        "customer_id": [f"CUST-{i % 20:03d}" for i in range(1, 101)],
        "order_date": ["2025-01-15"] * 50 + ["2025-02-20"] * 50,
        "region": ["North", "South", "East", "West"] * 25,
        "revenue": [100.0, 200.0, 300.0, 400.0] * 25,
        "cost": [50.0, 100.0, 150.0, 200.0] * 25,
        "order_status": ["Completed", "Pending", "Cancelled", "Completed"] * 25,
    }
    table = pa.Table.from_pydict(data)
    file_path = tmp_path / "sales_orders.parquet"
    pq.write_table(table, file_path)
    return file_path


@pytest.fixture
def sample_customers_parquet(tmp_path: Path) -> Path:
    """Creates a temporary Parquet file simulating customer dimensions."""
    data = {
        "customer_id": [f"CUST-{i:03d}" for i in range(20)],
        "customer_name": [f"Customer {i}" for i in range(20)],
        "segment": ["Enterprise", "SMB", "Consumer", "Enterprise"] * 5,
    }
    table = pa.Table.from_pydict(data)
    file_path = tmp_path / "customers.parquet"
    pq.write_table(table, file_path)
    return file_path


# =========================================================================
# 1. Intent Understanding & Analytical Query Planner
# =========================================================================

@pytest.mark.asyncio
async def test_planner_detects_ambiguity_and_asks_clarification():
    """Verifies that ambiguous questions trigger targeted clarification options."""
    mock_db = AsyncMock()

    # Ambiguous prompt
    plan, needs_clarify, prompt, options = await NLAQueryPlanner.plan_query(
        workspace_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        question="Show me the best performance",
        db=mock_db,
    )

    assert needs_clarify is True
    assert prompt is not None
    assert len(options) >= 2
    assert any("Revenue" in opt["label"] for opt in options)
    assert any("Volume" in opt["label"] for opt in options)


@pytest.mark.asyncio
async def test_planner_resolves_metrics_and_dimensions():
    """Verifies that unambiguous queries map to approved metrics and dimensions."""
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    mock_db = AsyncMock()

    # Setup mock semantic mappings
    mapping_revenue = ColumnSemanticMapping(
        id=uuid.uuid4(),
        dataset_id=dataset_id,
        dataset_version_id=version_id,
        column_name="revenue",
        business_name="Sales Revenue",
        is_measure=True,
        is_dimension=False,
        semantic_type="monetary",
        aggregation_method="SUM",
    )
    mapping_region = ColumnSemanticMapping(
        id=uuid.uuid4(),
        dataset_id=dataset_id,
        dataset_version_id=version_id,
        column_name="region",
        business_name="Sales Region",
        is_measure=False,
        is_dimension=True,
        semantic_type="categorical",
        aggregation_method="NONE",
    )

    # Setup mock metric
    metric_rev = MetricDefinition(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        dataset_id=dataset_id,
        name="Total Revenue",
        formula="SUM(revenue)",
        aggregation="SUM",
        approval_status="APPROVED",
    )

    # Mock execute results
    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        stmt_str = str(stmt)
        if "column_semantic_mappings" in stmt_str:
            mock_scalars.all.return_value = [mapping_revenue, mapping_region]
        elif "metric_definitions" in stmt_str:
            mock_scalars.all.return_value = [metric_rev]
        elif "dataset_relationships" in stmt_str:
            mock_scalars.all.return_value = []
        else:
            mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db.execute = mock_execute

    plan, needs_clarify, prompt, options = await NLAQueryPlanner.plan_query(
        workspace_id=ws_id,
        dataset_id=dataset_id,
        dataset_version_id=version_id,
        question="What is the top 5 revenue by region?",
        db=mock_db,
    )

    assert needs_clarify is False
    assert plan is not None
    assert plan.intent == "ranking"
    assert "region" in plan.group_by_columns
    assert plan.sort_direction == "desc"
    assert plan.limit == 5
    assert plan.metric_name == "Total Revenue"


# =========================================================================
# 2. Safe Query Compilation Engine & DuckDB Execution
# =========================================================================

def test_safe_compiler_protects_against_division_by_zero_and_injection(sample_sales_parquet: Path):
    """Verifies division-by-zero protection (NULLIF) and parameterized filtering."""
    plan = NLAQueryPlan(
        intent="group_by",
        target_dataset_id=uuid.uuid4(),
        metric_column="revenue",
        aggregation="SUM",
        group_by_columns=["region"],
        filters=[FilterItem(column="order_status", operator="eq", value="Completed")],
        sort_by="calculated_metric",
        sort_direction="desc",
        limit=10,
    )

    sql, params = NLASafeQueryCompiler.compile_to_duckdb_sql(
        plan=plan,
        primary_parquet_files=[sample_sales_parquet],
        metric_formula="SUM(revenue) / NULLIF(SUM(cost), 0)",
    )

    assert "NULLIF" in sql
    assert "?" in sql
    assert "LIMIT 10" in sql
    assert params == ["Completed"]

    # Execute with NLAQueryExecutor
    result = NLAQueryExecutor.execute_query(sql, params)
    assert result["row_count"] > 0
    assert "region" in result["columns"]
    assert len(result["rows"]) <= 10


def test_safe_compiler_prevents_sql_injection_in_columns():
    """Verifies that unsanitized column identifiers are rejected or sanitized."""
    plan = NLAQueryPlan(
        intent="performance",
        target_dataset_id=uuid.uuid4(),
        metric_column="revenue; DROP TABLE users; --",
        aggregation="SUM",
    )

    with pytest.raises(DataLensException):
        NLASafeQueryCompiler.compile_to_duckdb_sql(
            plan=plan,
            primary_parquet_files=[Path("dummy.parquet")],
        )


# =========================================================================
# 3. Multi-Dataset Analytics & Confirmed Joins
# =========================================================================

def test_safe_compiler_multi_dataset_left_join(
    sample_sales_parquet: Path,
    sample_customers_parquet: Path,
):
    """Verifies joined query execution across two Parquet datasets."""
    plan = NLAQueryPlan(
        intent="group_by",
        target_dataset_id=uuid.uuid4(),
        secondary_dataset_id=uuid.uuid4(),
        join_source_column="customer_id",
        join_target_column="customer_id",
        join_cardinality="MANY_TO_ONE",
        metric_column="revenue",
        aggregation="SUM",
        group_by_columns=["segment"],
        sort_by="calculated_metric",
        sort_direction="desc",
        limit=5,
    )

    sql, params = NLASafeQueryCompiler.compile_to_duckdb_sql(
        plan=plan,
        primary_parquet_files=[sample_sales_parquet],
        secondary_parquet_files=[sample_customers_parquet],
    )

    assert "LEFT JOIN" in sql
    assert 's."customer_id" = t."customer_id"' in sql

    # Execute against live DuckDB
    result = NLAQueryExecutor.execute_query(sql, params)
    assert result["row_count"] > 0
    assert "segment" in result["columns"]
    segments = [row["segment"] for row in result["rows"]]
    assert "Enterprise" in segments or "SMB" in segments or "Consumer" in segments


# =========================================================================
# 4. Evidence-Backed Numerical Verification & Hallucination Guard
# =========================================================================

def test_evidence_verifier_validates_and_flags_hallucinations():
    """Verifies that numbers cited in narrative are checked against DuckDB facts."""
    metric_cards = [
        {"title": "Total Revenue", "value": "$25,000", "numeric_value": 25000.0},
        {"title": "Average Order", "value": "$250", "numeric_value": 250.0},
    ]

    # Narrative citing matching numbers
    accurate_narrative = "Our Total Revenue reached 25000.0 with an average order value of 250."
    is_valid, warnings = NLAEvidenceVerifier.verify_cited_numbers(accurate_narrative, metric_cards)
    assert is_valid is True
    assert len(warnings) == 0

    # Narrative fabricating a number
    hallucinated_narrative = "Total Revenue was 999999.0 which represents a huge spike."
    is_valid_fake, warnings_fake = NLAEvidenceVerifier.verify_cited_numbers(hallucinated_narrative, metric_cards)
    assert is_valid_fake is False
    assert any("999999" in w for w in warnings_fake)


# =========================================================================
# 5. Visualization Recommendation Engine
# =========================================================================

def test_visualizer_recommends_appropriate_charts():
    """Verifies chart recommendation heuristics for line, bar, pie, and kpi."""
    # 1. Trend -> Line chart
    plan_trend = NLAQueryPlan(intent="trend", target_dataset_id=uuid.uuid4())
    chart_trend = NLAVisualizer.recommend_chart(
        plan=plan_trend,
        columns=["order_date", "calculated_metric"],
        rows=[{"order_date": "2025-01-01", "calculated_metric": 100}],
    )
    assert chart_trend is not None
    assert chart_trend.chart_type == "line"

    # 2. Ranking / Categorical -> Bar chart
    plan_rank = NLAQueryPlan(intent="ranking", target_dataset_id=uuid.uuid4())
    chart_rank = NLAVisualizer.recommend_chart(
        plan=plan_rank,
        columns=["region", "calculated_metric"],
        rows=[{"region": "North", "calculated_metric": 500}, {"region": "South", "calculated_metric": 300}],
    )
    assert chart_rank is not None
    assert chart_rank.chart_type == "bar"

    # 3. Contribution -> Pie / Donut
    plan_contrib = NLAQueryPlan(intent="contribution", target_dataset_id=uuid.uuid4())
    chart_contrib = NLAVisualizer.recommend_chart(
        plan=plan_contrib,
        columns=["region", "contribution_pct"],
        rows=[{"region": "North", "contribution_pct": 60.0}, {"region": "South", "contribution_pct": 40.0}],
    )
    assert chart_contrib is not None
    assert chart_contrib.chart_type == "pie"


# =========================================================================
# 6. Conversational Memory & Context Preservation
# =========================================================================

@pytest.mark.asyncio
async def test_planner_preserves_context_across_follow_ups():
    """Verifies that follow-up queries retain primary metrics, dimensions, and filter state."""
    prev_plan = NLAQueryPlan(
        intent="group_by",
        target_dataset_id=uuid.uuid4(),
        metric_column="revenue",
        aggregation="SUM",
        group_by_columns=["region"],
        filters=[FilterItem(column="order_status", operator="eq", value="Completed")],
        sort_direction="desc",
    )

    mock_db = AsyncMock()

    # Setup mock semantic mappings
    mapping_region = ColumnSemanticMapping(
        id=uuid.uuid4(),
        dataset_id=prev_plan.target_dataset_id,
        dataset_version_id=uuid.uuid4(),
        column_name="region",
        business_name="Sales Region",
        is_measure=False,
        is_dimension=True,
        semantic_type="categorical",
        aggregation_method="NONE",
    )

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        stmt_str = str(stmt)
        if "column_semantic_mappings" in stmt_str:
            mock_scalars.all.return_value = [mapping_region]
        else:
            mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db.execute = mock_execute

    # Follow-up: "Now only for North"
    merged_plan, needs_clarify, _, _ = await NLAQueryPlanner.plan_query(
        workspace_id=uuid.uuid4(),
        dataset_id=prev_plan.target_dataset_id,
        dataset_version_id=uuid.uuid4(),
        question="Now only for North",
        previous_plan=prev_plan,
        db=mock_db,
    )

    assert needs_clarify is False
    assert merged_plan.metric_column == "revenue"
    assert "region" in merged_plan.group_by_columns
    # Check that filter was added or merged
    filter_cols = [f.column for f in merged_plan.filters]
    assert "order_status" in filter_cols
    assert "region" in filter_cols
    region_filter = next(f for f in merged_plan.filters if f.column == "region")
    assert "north" in region_filter.value.lower()
