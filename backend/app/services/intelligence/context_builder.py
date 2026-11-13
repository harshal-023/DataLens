from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIPrivacyPolicy
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.intelligence import (
    BusinessContext,
    ColumnSemanticMapping,
    DatasetProfile,
    DatasetRelationship,
    MetricDefinition,
)


class AIContextBuilder:
    """
    Centralized semantic context builder for DataLens AI interactions.
    Constructs high-relevance, token-budgeted business schemas without exposing raw dataset rows.
    """

    MAX_COLUMNS_IN_CONTEXT = 40
    MAX_METRICS_IN_CONTEXT = 15

    @classmethod
    async def build_semantic_context(
        cls,
        dataset: Dataset,
        version: DatasetVersion,
        db: AsyncSession,
        user_query: str | None = None,
    ) -> dict[str, Any]:
        """
        Assembles verified semantic context, column business names, domain concepts,
        and registered metrics for LLM prompt formulation.
        """
        # 1. Fetch Privacy Policy
        p_stmt = select(AIPrivacyPolicy).where(AIPrivacyPolicy.workspace_id == dataset.workspace_id)
        p_res = await db.execute(p_stmt)
        policy = p_res.scalar_one_or_none()

        allow_samples = policy.allow_sample_values if policy else False

        # 2. Fetch Business Context
        bc_stmt = select(BusinessContext).where(BusinessContext.dataset_version_id == version.id)
        bc_res = await db.execute(bc_stmt)
        bcontext = bc_res.scalar_one_or_none()

        domain = bcontext.business_domain if bcontext else "GENERAL_BUSINESS"
        purpose = bcontext.purpose if bcontext else f"Dataset '{dataset.name}'"
        entities = bcontext.important_entities if bcontext else []
        limitations = bcontext.data_quality_limitations if bcontext else []

        # 3. Fetch Column Semantic Mappings
        col_stmt = (
            select(ColumnSemanticMapping)
            .where(ColumnSemanticMapping.dataset_version_id == version.id)
            .order_by(ColumnSemanticMapping.is_primary_key.desc(), ColumnSemanticMapping.is_measure.desc())
        )
        col_res = await db.execute(col_stmt)
        mappings = col_res.scalars().all()

        columns_context: list[dict[str, Any]] = []
        for m in mappings[: cls.MAX_COLUMNS_IN_CONTEXT]:
            c_entry: dict[str, Any] = {
                "name": m.column_name,
                "business_name": m.business_name,
                "logical_type": m.logical_type,
                "semantic_type": m.semantic_type,
                "role": "measure" if m.is_measure else ("primary_key" if m.is_primary_key else "dimension"),
                "suggested_aggregation": m.aggregation_method,
                "format": m.format_string,
            }
            columns_context.append(c_entry)

        # 4. Fetch Registered Metrics
        met_stmt = (
            select(MetricDefinition)
            .where(
                MetricDefinition.workspace_id == dataset.workspace_id,
                (MetricDefinition.dataset_id == dataset.id) | (MetricDefinition.dataset_id.is_(None)),
                MetricDefinition.approval_status == "APPROVED",
            )
            .limit(cls.MAX_METRICS_IN_CONTEXT)
        )
        met_res = await db.execute(met_stmt)
        metrics = met_res.scalars().all()

        metrics_context: list[dict[str, Any]] = [
            {
                "name": m.name,
                "formula": m.formula,
                "aggregation": m.aggregation,
                "formatting": m.formatting,
                "description": m.description,
            }
            for m in metrics
        ]

        # 5. Fetch Confirmed Relationships
        rel_stmt = (
            select(DatasetRelationship)
            .where(
                DatasetRelationship.workspace_id == dataset.workspace_id,
                (DatasetRelationship.source_dataset_id == dataset.id)
                | (DatasetRelationship.target_dataset_id == dataset.id),
                DatasetRelationship.status == "CONFIRMED",
            )
        )
        rel_res = await db.execute(rel_stmt)
        relationships = rel_res.scalars().all()

        relationships_context: list[dict[str, Any]] = [
            {
                "source_column": r.source_column,
                "target_column": r.target_column,
                "relationship_type": r.relationship_type,
            }
            for r in relationships
        ]

        # 6. Fetch Profile for Quality Score
        prof_stmt = select(DatasetProfile).where(DatasetProfile.dataset_version_id == version.id)
        prof_res = await db.execute(prof_stmt)
        profile = prof_res.scalar_one_or_none()
        quality_score = profile.quality_score if profile else 100

        # Construct concise prompt-ready string
        prompt_lines: list[str] = [
            f"Dataset: {dataset.name} (Rows: {version.row_count:,}, Quality Score: {quality_score}/100)",
            f"Business Domain: {domain}",
            f"Purpose: {purpose}",
        ]
        if entities:
            prompt_lines.append(f"Key Entities: {', '.join(entities)}")

        prompt_lines.append("\nColumns & Semantic Meanings:")
        for c in columns_context:
            role_desc = f"[{c['role'].upper()}]"
            fmt_desc = f", format: {c['format']}" if c.get("format") else ""
            prompt_lines.append(
                f"- {c['name']} (as '{c['business_name']}'): {c['logical_type']}, {c['semantic_type']} "
                f"{role_desc}, default_agg: {c['suggested_aggregation']}{fmt_desc}"
            )

        if metrics_context:
            prompt_lines.append("\nApproved Business Metrics:")
            for m in metrics_context:
                prompt_lines.append(f"- {m['name']} = {m['formula']} ({m['formatting']})")

        if relationships_context:
            prompt_lines.append("\nData Relationships:")
            for r in relationships_context:
                prompt_lines.append(
                    f"- {r['source_column']} -> {r['target_column']} ({r['relationship_type']})"
                )

        if limitations:
            prompt_lines.append(f"\nData Quality Limitations: {'; '.join(limitations)}")

        formatted_summary = "\n".join(prompt_lines)

        return {
            "dataset_name": dataset.name,
            "version_number": version.version_number,
            "total_rows": version.row_count,
            "quality_score": quality_score,
            "business_domain": domain,
            "purpose": purpose,
            "entities": entities,
            "columns": columns_context,
            "metrics": metrics_context,
            "relationships": relationships_context,
            "formatted_summary": formatted_summary,
            "allow_sample_values": allow_samples,
        }
