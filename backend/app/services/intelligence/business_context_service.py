from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.intelligence import BusinessContext, ColumnSemanticMapping


class BusinessContextEngine:
    """
    Infers business domain, analytical purpose, key entities, and suggested KPIs
    from dataset profiling signals and semantic mappings.
    """

    DOMAIN_SIGNALS: dict[str, list[str]] = {
        "SALES": [
            "revenue", "order", "sales", "price", "subtotal", "mrp", "discount",
            "quantity", "customer", "product", "item", "invoice", "deal"
        ],
        "FINANCE": [
            "expense", "profit", "margin", "tax", "budget", "ledger", "balance",
            "asset", "liability", "cost_of_goods", "cogs", "ebitda", "cashflow"
        ],
        "MARKETING": [
            "campaign", "impressions", "clicks", "ctr", "conversion", "spend",
            "ad", "channel", "leads", "cpc", "cpa", "cpm", "attribution"
        ],
        "CUSTOMER_ANALYTICS": [
            "churn", "retention", "ltv", "lifetime_value", "nps", "segment",
            "satisfaction", "engagement", "subscriber", "cohort"
        ],
        "OPERATIONS": [
            "incident", "ticket", "sla", "resolution_time", "uptime", "downtime",
            "throughput", "efficiency", "backlog", "queue"
        ],
        "INVENTORY": [
            "stock", "inventory", "warehouse", "reorder", "quantity_on_hand",
            "safety_stock", "sku", "shelf_life", "supplier", "bin"
        ],
        "HUMAN_RESOURCES": [
            "employee", "salary", "hire_date", "attrition", "department",
            "headcount", "performance", "bonus", "tenure", "job_title"
        ],
        "LOGISTICS": [
            "shipment", "delivery", "carrier", "freight", "tracking",
            "transit_time", "destination", "origin", "dispatch", "port"
        ],
    }

    SUGGESTED_DOMAIN_KPIS: dict[str, list[dict[str, str]]] = {
        "SALES": [
            {"name": "Total Revenue", "formula": "SUM(revenue)", "description": "Sum of total sales revenue"},
            {"name": "Total Orders", "formula": "COUNT(DISTINCT order_id)", "description": "Total volume of unique orders"},
            {"name": "Average Order Value", "formula": "Revenue / Total Orders", "description": "Average revenue generated per order"},
        ],
        "FINANCE": [
            {"name": "Gross Profit", "formula": "Revenue - Cost", "description": "Net revenue after subtracting direct costs"},
            {"name": "Profit Margin", "formula": "Gross Profit / Revenue * 100", "description": "Percentage profit margin"},
        ],
        "MARKETING": [
            {"name": "Click-Through Rate", "formula": "Clicks / Impressions * 100", "description": "Percentage of ad impressions leading to clicks"},
            {"name": "Conversion Rate", "formula": "Conversions / Clicks * 100", "description": "Percentage of clicks resulting in conversions"},
        ],
        "INVENTORY": [
            {"name": "Total Stock Units", "formula": "SUM(quantity_on_hand)", "description": "Total inventory units in stock"},
            {"name": "Total Stock Valuation", "formula": "SUM(stock_value)", "description": "Monetary value of inventory on hand"},
        ],
        "GENERAL_BUSINESS": [
            {"name": "Total Record Count", "formula": "COUNT(*)", "description": "Total volume of records"},
        ],
    }

    @classmethod
    def classify_domain(cls, column_names: list[str], semantic_types: list[str]) -> tuple[str, float]:
        """
        Calculates signal overlap across business domains.
        """
        tokens = set()
        for name in column_names:
            tokens.update(name.lower().replace("-", "_").split("_"))
        tokens.update(t.lower() for t in semantic_types)

        best_domain = "GENERAL_BUSINESS"
        best_score = 0.0

        for domain, signals in cls.DOMAIN_SIGNALS.items():
            matches = sum(1 for s in signals if s in tokens)
            score = matches / len(signals)
            if score > best_score and matches >= 2:
                best_score = score
                best_domain = domain

        confidence = min(0.95, round(0.5 + (best_score * 0.5), 2)) if best_domain != "GENERAL_BUSINESS" else 0.60
        return best_domain, confidence

    @classmethod
    async def generate_and_persist_context(
        cls,
        dataset: Dataset,
        version: DatasetVersion,
        mappings: list[ColumnSemanticMapping],
        db: AsyncSession,
    ) -> BusinessContext:
        """
        Synthesizes business context, purpose, entities, and suggested KPIs,
        and persists into the database for the dataset version.
        """
        col_names = [m.column_name for m in mappings]
        sem_types = [m.semantic_type for m in mappings]

        domain, _ = cls.classify_domain(col_names, sem_types)

        # Entities
        entities: list[str] = []
        for m in mappings:
            if "customer" in m.semantic_type or "customer" in m.column_name.lower():
                if "Customer" not in entities:
                    entities.append("Customer")
            if "product" in m.semantic_type or "product" in m.column_name.lower() or "item" in m.column_name.lower():
                if "Product" not in entities:
                    entities.append("Product")
            if "transaction" in m.semantic_type or "order" in m.column_name.lower():
                if "Order" not in entities:
                    entities.append("Order")
            if "employee" in m.column_name.lower():
                if "Employee" not in entities:
                    entities.append("Employee")

        key_dims = [m.business_name for m in mappings if m.is_dimension][:6]
        key_meas = [m.business_name for m in mappings if m.is_measure][:6]

        # Suggested KPIs adapted to available columns
        suggested_kpis = cls.SUGGESTED_DOMAIN_KPIS.get(
            domain, cls.SUGGESTED_DOMAIN_KPIS["GENERAL_BUSINESS"]
        )

        purpose = (
            f"Dataset containing {version.row_count:,} records of {domain.lower().replace('_', ' ')} operations, "
            f"covering key business entities: {', '.join(entities) if entities else 'general attributes'}."
        )

        limitations: list[str] = []
        assumptions: list[str] = [
            "Analytical calculations assume verified DuckDB aggregation without sample extrapolation."
        ]

        # Check existing
        stmt = select(BusinessContext).where(BusinessContext.dataset_version_id == version.id)
        res = await db.execute(stmt)
        bcontext = res.scalar_one_or_none()

        if not bcontext:
            bcontext = BusinessContext(
                dataset_version_id=version.id,
                dataset_id=dataset.id,
                business_domain=domain,
                purpose=purpose,
                important_entities=entities,
                key_dimensions=key_dims,
                important_measures=key_meas,
                suggested_kpis=suggested_kpis,
                data_quality_limitations=limitations,
                business_assumptions=assumptions,
                is_user_confirmed=False,
            )
            db.add(bcontext)
        else:
            if not bcontext.is_user_confirmed:
                bcontext.business_domain = domain
                bcontext.purpose = purpose
                bcontext.important_entities = entities
                bcontext.key_dimensions = key_dims
                bcontext.important_measures = key_meas
                bcontext.suggested_kpis = suggested_kpis

        await db.flush()
        return bcontext
