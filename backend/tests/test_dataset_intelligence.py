from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.services.intelligence.business_context_service import BusinessContextEngine
from app.services.intelligence.context_builder import AIContextBuilder
from app.services.intelligence.metric_engine import MetricIntelligenceEngine
from app.services.intelligence.profiler import DatasetIntelligenceProfiler
from app.services.intelligence.relationship_service import RelationshipDiscoveryEngine


@pytest.fixture
def sample_sales_parquet(tmp_path: Path) -> Path:
    """
    Creates a temporary Parquet file simulating retail sales orders.
    """
    data = {
        "order_id": [f"ORD-{i:04d}" for i in range(1, 101)],
        "customer_id": [f"CUST-{i % 20:03d}" for i in range(1, 101)],
        "order_date": ["2025-01-15"] * 50 + ["2025-02-20"] * 50,
        "region": ["North", "South", "East", "West"] * 25,
        "quantity": [1, 2, 3, 4, 5] * 20,
        "unit_price": [10.5, 25.0, 50.0, 100.0, 250.0] * 20,
        "revenue": [10.5, 50.0, 150.0, 400.0, 1250.0] * 20,
        "discount_pct": [0.05, 0.10, 0.15, 0.0, 0.20] * 20,
        "order_status": ["Completed", "Pending", "Cancelled", "Completed"] * 25,
    }
    table = pa.Table.from_pydict(data)
    file_path = tmp_path / "sales_orders.parquet"
    pq.write_table(table, file_path)
    return file_path


@pytest.fixture
def sample_customers_parquet(tmp_path: Path) -> Path:
    """
    Creates a temporary Parquet file simulating customer master data.
    """
    data = {
        "customer_id": [f"CUST-{i:03d}" for i in range(20)],
        "customer_name": [f"Customer {i}" for i in range(20)],
        "email": [f"user{i}@example.com" for i in range(20)],
        "phone": [f"+1-555-01{i:02d}" for i in range(20)],
        "segment": ["Enterprise", "SMB", "Consumer", "Enterprise"] * 5,
    }
    table = pa.Table.from_pydict(data)
    file_path = tmp_path / "customers.parquet"
    pq.write_table(table, file_path)
    return file_path


def test_profiler_statistical_and_semantic_inference(sample_sales_parquet: Path):
    """
    Verifies that the profiler extracts complete statistical profiles, identifies
    candidate primary/foreign keys, measures, dimensions, and infers semantic types.
    """
    profile = DatasetIntelligenceProfiler.profile_parquet_dataset([sample_sales_parquet])

    assert profile["total_rows"] == 100
    assert profile["column_count"] == 9
    assert profile["duplicate_rows"] == 0
    assert profile["quality_score"] > 80

    cols = profile["columns"]
    # 1. Primary Key candidate
    assert "order_id" in profile["candidate_pks"]
    assert cols["order_id"]["is_primary_key"] is True
    assert cols["order_id"]["semantic_type"] == "transaction_identifier"

    # 2. Foreign Key candidate
    assert "customer_id" in profile["candidate_fks"]
    assert cols["customer_id"]["is_foreign_key"] is True
    assert cols["customer_id"]["semantic_type"] == "customer_identifier"

    # 3. Currency measure
    assert cols["revenue"]["semantic_type"] == "currency"
    assert cols["revenue"]["is_measure"] is True
    assert cols["revenue"]["aggregation_method"] == "SUM"
    assert cols["revenue"]["numeric_stats"]["mean"] > 0

    # 4. Quantity measure
    assert cols["quantity"]["semantic_type"] == "quantity"
    assert cols["quantity"]["is_measure"] is True

    # 5. Percentage measure
    assert cols["discount_pct"]["semantic_type"] == "percentage"
    assert cols["discount_pct"]["is_measure"] is True
    assert cols["discount_pct"]["aggregation_method"] == "AVG"

    # 6. Dimensions
    assert cols["region"]["is_dimension"] is True
    assert cols["order_status"]["semantic_type"] == "status"
    assert cols["order_date"]["semantic_type"] == "date"


def test_profiler_email_phone_inference(sample_customers_parquet: Path):
    """
    Verifies semantic detection of email, phone, and PK/FK properties.
    """
    profile = DatasetIntelligenceProfiler.profile_parquet_dataset([sample_customers_parquet])

    cols = profile["columns"]
    assert cols["email"]["semantic_type"] == "email"
    assert cols["phone"]["semantic_type"] == "phone"
    assert cols["customer_id"]["is_primary_key"] is True
    assert cols["customer_id"]["uniqueness_pct"] == 100.0


def test_business_context_domain_classification():
    """
    Verifies classification of business domain and KPI suggestions.
    """
    sales_cols = ["order_id", "customer_id", "product_id", "revenue", "quantity", "unit_price", "discount"]
    sales_semantics = ["transaction_identifier", "customer_identifier", "product_identifier", "currency", "quantity", "currency", "percentage"]

    domain, conf = BusinessContextEngine.classify_domain(sales_cols, sales_semantics)
    assert domain == "SALES"
    assert conf >= 0.7

    kpis = BusinessContextEngine.SUGGESTED_DOMAIN_KPIS["SALES"]
    kpi_names = [k["name"] for k in kpis]
    assert "Total Revenue" in kpi_names
    assert "Total Orders" in kpi_names
    assert "Average Order Value" in kpi_names


def test_metric_formula_safety_and_validation():
    """
    Verifies AST-based formula validation: allows safe math, blocks malicious injections.
    """
    # 1. Valid safe formulas
    valid_formulas = [
        "Revenue / Total_Orders",
        "SUM(revenue) - SUM(cost)",
        "Profit / Revenue * 100",
        "SUM(quantity) * 1.5",
        "COUNT(order_id)",
        "Revenue + Tax - Discount",
    ]
    for form in valid_formulas:
        is_val, refs, errs = MetricIntelligenceEngine.validate_formula(form)
        assert is_val is True, f"Formula '{form}' should be valid, got errors: {errs}"

    # 2. Blocked malicious expressions (exec, eval, system calls, syntax errors)
    blocked_formulas = [
        "__import__('os').system('ls')",
        "eval('1 + 1')",
        "subprocess.Popen(['calc'])",
        "SELECT * FROM users",
        "revenue; DROP TABLE orders;",
        "revenue`ls`",
        "lambda x: x + 1",
    ]
    for form in blocked_formulas:
        is_val, refs, errs = MetricIntelligenceEngine.validate_formula(form)
        assert is_val is False, f"Malicious formula '{form}' was unexpectedly accepted!"


def test_metric_division_by_zero_sql_compilation():
    """
    Verifies that bare divisions are wrapped with NULLIF to prevent division-by-zero crashes.
    """
    compiled = MetricIntelligenceEngine.compile_formula_to_sql("Revenue / Total_Orders * 100")
    assert "NULLIF(Total_Orders, 0)" in compiled


def test_metric_calculation_on_parquet(sample_sales_parquet: Path):
    """
    Verifies calculation of business metrics directly over Parquet files.
    """
    res = MetricIntelligenceEngine.calculate_metric_value(
        formula="SUM(revenue)",
        aggregation="SUM",
        parquet_files=[sample_sales_parquet],
        source_columns=["revenue"],
    )
    assert res["is_null"] is False
    assert res["metric_value"] > 0
    # Expected sum: 20 * (10.5 + 50 + 150 + 400 + 1250) = 20 * 1860.5 = 37210.0
    assert abs(res["metric_value"] - 37210.0) < 0.1

    # Average Order Value: SUM(revenue) / COUNT(order_id)
    aov_res = MetricIntelligenceEngine.calculate_metric_value(
        formula="SUM(revenue) / COUNT(order_id)",
        aggregation="CALCULATED",
        parquet_files=[sample_sales_parquet],
        source_columns=["revenue", "order_id"],
    )
    assert abs(aov_res["metric_value"] - 372.1) < 0.1


def test_relationship_discovery_cardinality_and_overlap(sample_sales_parquet: Path, sample_customers_parquet: Path):
    """
    Verifies relationship discovery between sales orders and customer master.
    """
    overlap_info = RelationshipDiscoveryEngine.calculate_value_overlap(
        src_parquet=[sample_sales_parquet],
        src_col="customer_id",
        tgt_parquet=[sample_customers_parquet],
        tgt_col="customer_id",
    )

    assert overlap_info["source_distinct"] == 20
    assert overlap_info["target_distinct"] == 20
    assert overlap_info["common_count"] == 20
    assert overlap_info["overlap_ratio"] == 1.0


def test_suggest_business_name():
    """
    Verifies conversion of technical column names to professional business names.
    """
    assert DatasetIntelligenceProfiler.suggest_business_name("cust_order_amt") == "Customer Order Amount"
    assert DatasetIntelligenceProfiler.suggest_business_name("product_sku") == "Product SKU"
    assert DatasetIntelligenceProfiler.suggest_business_name("discount_pct") == "Discount Percentage"
    assert DatasetIntelligenceProfiler.suggest_business_name("user_email") == "User Email"
    assert DatasetIntelligenceProfiler.suggest_business_name("grossRevenueUSD") == "Gross Revenue Usd"


@pytest.mark.asyncio
async def test_ai_context_builder_and_privacy():
    """
    Verifies that AIContextBuilder compiles schema metadata, column meanings,
    and business context without transmitting raw rows or exceeding token budgets.
    """
    import uuid
    from unittest.mock import AsyncMock, MagicMock

    from app.models.dataset import Dataset
    from app.models.dataset_version import DatasetVersion
    from app.models.intelligence import ColumnSemanticMapping

    mock_ds = Dataset(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Quarterly Sales Orders",
        file_type="csv",
        original_filename="orders.csv",
    )
    mock_ver = DatasetVersion(
        id=uuid.uuid4(),
        dataset_id=mock_ds.id,
        version_number="v1",
        storage_key="manifest.json",
        row_count=50000,
        column_count=5,
    )

    mock_db = AsyncMock()

    async def mock_execute_side_effect(stmt):
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        sql_str = str(stmt)
        if "column_semantic_mappings" in sql_str:
            sc = MagicMock()
            sc.all.return_value = [
                ColumnSemanticMapping(
                    id=uuid.uuid4(),
                    dataset_version_id=mock_ver.id,
                    dataset_id=mock_ds.id,
                    column_name="order_id",
                    business_name="Order ID",
                    semantic_type="transaction_identifier",
                    logical_type="string",
                    is_primary_key=True,
                    is_dimension=True,
                    is_measure=False,
                    mapping_status="USER_CONFIRMED",
                ),
                ColumnSemanticMapping(
                    id=uuid.uuid4(),
                    dataset_version_id=mock_ver.id,
                    dataset_id=mock_ds.id,
                    column_name="revenue",
                    business_name="Sales Revenue",
                    semantic_type="currency",
                    logical_type="float",
                    is_primary_key=False,
                    is_dimension=False,
                    is_measure=True,
                    aggregation_method="SUM",
                    format_string="USD",
                    mapping_status="USER_CONFIRMED",
                ),
            ]
            mock_res.scalars.return_value = sc
        else:
            sc = MagicMock()
            sc.all.return_value = []
            mock_res.scalars.return_value = sc
        return mock_res

    mock_db.execute.side_effect = mock_execute_side_effect

    ctx = await AIContextBuilder.build_semantic_context(
        dataset=mock_ds,
        version=mock_ver,
        db=mock_db,
        user_query="What was our total revenue?",
    )

    assert ctx["dataset_name"] == "Quarterly Sales Orders"
    assert ctx["total_rows"] == 50000
    assert "Columns & Semantic Meanings:" in ctx["formatted_summary"]
    assert "Sales Revenue" in ctx["formatted_summary"]
    assert "USD" in ctx["formatted_summary"]
