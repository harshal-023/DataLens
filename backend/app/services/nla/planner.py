import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import (
    ColumnSemanticMapping,
    DatasetRelationship,
    MetricDefinition,
)
from app.services.nla.schemas import FilterItem, NLAQueryPlan


class NLAQueryPlanner:
    """
    Semantic-aware analytical query planner.
    Translates natural-language business questions into structured, validated
    analytical plans grounded in approved metrics, semantic mappings, and relationships.
    """

    AMBIGUOUS_PATTERNS = [
        r"^(show|tell|give)\s+(me\s+)?(the\s+)?(best\s+)?(sales|performance|numbers|data|stats|metrics)(\?)?$",
        r"^(sales|performance|analytics)(\?)?\s*$",
        r"^(how\s+are\s+we\s+doing)(\?)?$",
        r"^(how\s+did\s+we\s+do)(\?)?$",
        r"^what\s+(is|about)\s+(the\s+)?(performance|sales|numbers)(\?)?$",
    ]

    @classmethod
    def check_ambiguity(cls, question: str) -> tuple[bool, list[str]]:
        """
        Detects ambiguous inquiries and generates targeted clarification choices.
        """
        clean = question.strip().lower()
        for pat in cls.AMBIGUOUS_PATTERNS:
            if re.match(pat, clean):
                return True, [
                    "Total Revenue",
                    "Total Order Volume",
                    "Average Order Value",
                    "Revenue Trend Over Time",
                ]
        return False, []

    @classmethod
    async def plan_query(
        cls,
        workspace_id: uuid.UUID,
        dataset_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        question: str,
        db: AsyncSession,
        previous_plan: NLAQueryPlan | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[NLAQueryPlan, bool, str | None, list[dict[str, Any]]]:
        active_ctx: dict[str, Any] = {}
        if previous_plan:
            active_ctx["previous_plan"] = previous_plan.model_dump()
        plan, _ = await cls.formulate_plan(
            question=question,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            db=db,
            active_context=active_ctx,
            conversation_history=conversation_history,
        )
        opts: list[dict[str, Any]] = [
            opt.model_dump() if hasattr(opt, "model_dump") else (opt if isinstance(opt, dict) else {"label": str(opt)})
            for opt in plan.clarification_options
        ]
        return (
            plan,
            plan.needs_clarification,
            plan.clarification_prompt,
            opts,
        )

    @classmethod
    async def formulate_plan(
        cls,
        question: str,
        workspace_id: uuid.UUID,
        dataset_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        db: AsyncSession,
        active_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[NLAQueryPlan, str | None]:
        """
        Formulates structured plan by resolving metrics, semantics, relationships,
        and follow-up conversational context.
        Returns: (plan, resolved_metric_formula)
        """
        q_lower = question.lower().strip()
        active_ctx = active_context or {}

        # 1. Ambiguity Check
        is_ambiguous, clarify_opts = cls.check_ambiguity(question)
        if is_ambiguous:
            clarify_msg = "Your question is broad. Which key business metric would you like to evaluate?"
            return NLAQueryPlan(
                intent="performance",
                needs_clarification=True,
                clarification_options=clarify_opts,
                clarification_message=clarify_msg,
                clarification_prompt=clarify_msg,
            ), None

        # 2. Fetch Semantic Mappings for this dataset version
        col_stmt = select(ColumnSemanticMapping).where(
            ColumnSemanticMapping.dataset_version_id == dataset_version_id
        )
        col_res = await db.execute(col_stmt)
        mappings = col_res.scalars().all()
        mapping_by_name = {m.column_name.lower(): m for m in mappings}
        for m in mappings:
            if m.business_name:
                mapping_by_name[m.business_name.lower()] = m

        # 3. Fetch Approved Metrics in Workspace
        met_stmt = select(MetricDefinition).where(
            MetricDefinition.workspace_id == workspace_id,
            (MetricDefinition.dataset_id == dataset_id) | (MetricDefinition.dataset_id.is_(None)),
            MetricDefinition.approval_status == "APPROVED",
        )
        met_res = await db.execute(met_stmt)
        metrics = met_res.scalars().all()
        metric_by_name = {m.name.lower(): m for m in metrics}

        # 4. Fetch Confirmed Relationships
        rel_stmt = select(DatasetRelationship).where(
            DatasetRelationship.workspace_id == workspace_id,
            (DatasetRelationship.source_dataset_id == dataset_id)
            | (DatasetRelationship.target_dataset_id == dataset_id),
            DatasetRelationship.status == "CONFIRMED",
        )
        rel_res = await db.execute(rel_stmt)
        relationships = rel_res.scalars().all()

        # 5. Intent Classification
        intent = "performance"
        time_granularity = "monthly"
        sort_dir = "desc"
        limit_val = 20
        comparison_period = None

        if any(w in q_lower for w in ("trend", "over time", "monthly", "growth", "daily", "quarterly")):
            intent = "time_series"
            if "daily" in q_lower:
                time_granularity = "daily"
            elif "quarterly" in q_lower:
                time_granularity = "quarterly"
            elif "yearly" in q_lower:
                time_granularity = "yearly"
        elif any(w in q_lower for w in ("top", "highest", "best", "rank", "bottom", "lowest")):
            intent = "ranking"
            if any(w in q_lower for w in ("bottom", "lowest")):
                sort_dir = "asc"
            limit_val = 5 if "top 5" in q_lower else 10
        elif any(w in q_lower for w in ("share", "contribution", "percent of", "percentage of")):
            intent = "contribution"
        elif any(w in q_lower for w in ("compare", "versus", "vs", "last year", "last month", "prior")):
            intent = "comparison"
            if "last year" in q_lower or "yoy" in q_lower:
                comparison_period = "yoy"
            elif "last month" in q_lower or "mom" in q_lower:
                comparison_period = "mom"
            elif "quarter" in q_lower:
                comparison_period = "qoq"
        elif any(w in q_lower for w in ("why", "decline", "increase", "drop", "diagnostic")):
            intent = "diagnostic"

        # 6. Resolve Metric
        resolved_metric: MetricDefinition | None = None
        metric_col: str | None = None
        metric_formula: str | None = None

        # Check registered approved metrics first (exact substring or token overlap)
        for m_name, m_obj in metric_by_name.items():
            if m_name in q_lower or any(word in m_name for word in q_lower.split() if len(word) > 3):
                resolved_metric = m_obj
                metric_formula = m_obj.formula
                metric_col = m_obj.source_columns[0] if m_obj.source_columns else None
                break

        # Fallback to column mappings for measures
        if not resolved_metric:
            for m in mappings:
                if m.is_measure and (
                    m.column_name.lower() in q_lower or (m.business_name and m.business_name.lower() in q_lower)
                ):
                    metric_col = m.column_name
                    # Check if an approved metric matches this column
                    for m_obj in metric_by_name.values():
                        if m_obj.source_columns and m.column_name in m_obj.source_columns:
                            resolved_metric = m_obj
                            metric_formula = m_obj.formula
                            break
                    break

        # Check context memory if follow-up
        prev_plan_dict = active_ctx.get("previous_plan") or {}
        prev_m_col = prev_plan_dict.get("metric_column")
        prev_m_name = prev_plan_dict.get("metric_name") or active_ctx.get("active_metric_name")
        if not resolved_metric and not metric_col and (prev_m_name or prev_m_col):
            if prev_m_name and prev_m_name.lower() in metric_by_name:
                resolved_metric = metric_by_name[prev_m_name.lower()]
                metric_formula = resolved_metric.formula
                metric_col = resolved_metric.source_columns[0] if resolved_metric.source_columns else prev_m_col
            elif prev_m_col:
                metric_col = prev_m_col

        # Default fallback metric
        if not resolved_metric and not metric_col:
            measures = [m.column_name for m in mappings if m.is_measure]
            metric_col = measures[0] if measures else (mappings[0].column_name if mappings else "id")

        # 7. Resolve Dimensions (Group By)
        group_by: list[str] = []
        for m in mappings:
            if m.is_dimension and (
                m.column_name.lower() in q_lower or (m.business_name and m.business_name.lower() in q_lower)
            ):
                if m.column_name not in group_by:
                    group_by.append(m.column_name)

        # Merge conversational dimensions if follow-up and none specified in new query
        if not group_by and prev_plan_dict.get("group_by_columns"):
            group_by = list(prev_plan_dict["group_by_columns"])
        elif not group_by and intent in ("ranking", "contribution", "diagnostic") and active_ctx.get("active_dimensions"):
            group_by = list(active_ctx["active_dimensions"])

        # Default dimension for ranking if still empty
        if not group_by and intent in ("ranking", "contribution"):
            dims = [m.column_name for m in mappings if m.is_dimension and not m.is_primary_key]
            if dims:
                group_by.append(dims[0])

        # 8. Resolve Date Column
        date_col: str | None = None
        for m in mappings:
            if m.semantic_type in ("date", "timestamp") or m.logical_type in ("date", "datetime"):
                date_col = m.column_name
                break

        # 9. Resolve Filters
        filters: list[FilterItem] = []
        # Check for categorical value filter matches in query
        for m in mappings:
            if m.is_dimension:
                # E.g. "Only Maharashtra" or "for Maharashtra"
                col_name = m.column_name
                match = re.search(r"\b(?:in|for|only)\s+([a-zA-Z0-9_\s]+)", q_lower)
                if match:
                    extracted_val = match.group(1).strip()
                    # If matches known categorical tokens
                    if extracted_val and len(extracted_val) > 2 and extracted_val not in ("the", "this", "last"):
                        filters.append(FilterItem(column=col_name, operator="contains", value=extracted_val))

        # Merge previous filters if follow-up
        prev_filters = prev_plan_dict.get("filters") or active_ctx.get("active_filters") or []
        for prev_f in prev_filters:
            col_f = prev_f["column"] if isinstance(prev_f, dict) else prev_f.column
            op_f = prev_f.get("operator", "eq") if isinstance(prev_f, dict) else prev_f.operator
            val_f = prev_f.get("value") if isinstance(prev_f, dict) else prev_f.value
            if not any(f.column == col_f for f in filters):
                filters.append(FilterItem(column=col_f, operator=op_f, value=val_f))

        # 10. Multi-Dataset Join Resolution
        secondary_ds_id = None
        join_src = None
        join_tgt = None
        join_card = None

        if relationships and any(w in q_lower for w in ("customer", "segment", "product", "supplier", "region", "client")):
            for rel in relationships:
                # Check if query references columns from target dataset
                target_ds_id = rel.target_dataset_id if rel.source_dataset_id == dataset_id else rel.source_dataset_id
                secondary_ds_id = target_ds_id
                join_src = rel.source_column
                join_tgt = rel.target_column
                join_card = rel.relationship_type
                break

        plan = NLAQueryPlan(
            intent=intent,
            metric_name=resolved_metric.name if resolved_metric else (metric_col or "").title(),
            metric_column=metric_col,
            aggregation=resolved_metric.aggregation if resolved_metric else "SUM",
            group_by_columns=group_by,
            filters=filters,
            date_column=date_col,
            time_granularity=time_granularity,
            comparison_period=comparison_period,
            sort_direction=sort_dir,
            limit=limit_val,
            secondary_dataset_id=secondary_ds_id,
            join_source_column=join_src,
            join_target_column=join_tgt,
            join_cardinality=join_card,
            needs_clarification=False,
        )

        return plan, metric_formula
