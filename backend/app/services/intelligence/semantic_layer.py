import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataLensException
from app.core.logging import logger
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.intelligence import (
    BusinessEntity,
    ColumnSemanticMapping,
    DatasetProfile,
)


class SemanticLayerService:
    """
    Manages semantic definitions, user confirmations, entity bindings, and
    cross-version schema inheritance for DataLens datasets.
    """

    STANDARD_ENTITIES = [
        {"name": "Customer", "pattern": r"(customer|client|buyer|user)_id", "type": "STANDARD"},
        {"name": "Product", "pattern": r"(product|item|sku|part)_id", "type": "STANDARD"},
        {"name": "Order", "pattern": r"(order|invoice|txn|transaction)_id", "type": "STANDARD"},
        {"name": "Transaction", "pattern": r"(transaction|payment|receipt)_id", "type": "STANDARD"},
        {"name": "Employee", "pattern": r"(employee|staff|agent|rep)_id", "type": "STANDARD"},
        {"name": "Supplier", "pattern": r"(supplier|vendor|provider)_id", "type": "STANDARD"},
        {"name": "Location", "pattern": r"(location|store|warehouse|branch)_id", "type": "STANDARD"},
        {"name": "Campaign", "pattern": r"(campaign|ad|promotion)_id", "type": "STANDARD"},
    ]

    @classmethod
    async def ensure_standard_entities(
        cls, workspace_id: uuid.UUID, db: AsyncSession
    ) -> list[BusinessEntity]:
        """
        Ensures the standard business entities exist for a workspace.
        """
        stmt = select(BusinessEntity).where(BusinessEntity.workspace_id == workspace_id)
        res = await db.execute(stmt)
        existing = {e.name: e for e in res.scalars().all()}

        created: list[BusinessEntity] = []
        for ent in cls.STANDARD_ENTITIES:
            if ent["name"] not in existing:
                new_ent = BusinessEntity(
                    workspace_id=workspace_id,
                    name=ent["name"],
                    description=f"Standard business entity for {ent['name']}.",
                    entity_type=ent["type"],
                    identifying_column_pattern=ent["pattern"],
                )
                db.add(new_ent)
                created.append(new_ent)

        if created:
            await db.flush()
        return list(existing.values()) + created

    @classmethod
    async def persist_profile_and_semantics(
        cls,
        dataset: Dataset,
        version: DatasetVersion,
        profile_data: dict[str, Any],
        db: AsyncSession,
    ) -> tuple[DatasetProfile, list[ColumnSemanticMapping]]:
        """
        Persists profile results and synchronizes column semantic mappings,
        respecting existing user-confirmed mappings.
        """
        # 1. Upsert DatasetProfile
        stmt = select(DatasetProfile).where(DatasetProfile.dataset_version_id == version.id)
        res = await db.execute(stmt)
        db_profile = res.scalar_one_or_none()

        if not db_profile:
            db_profile = DatasetProfile(
                dataset_version_id=version.id,
                dataset_id=dataset.id,
                row_count=profile_data["total_rows"],
                column_count=profile_data["column_count"],
                duplicate_rows=profile_data.get("duplicate_rows", 0),
                quality_score=profile_data.get("quality_score", 100),
                profile_metadata=profile_data.get("columns", {}),
                warnings=profile_data.get("warnings", []),
            )
            db.add(db_profile)
        else:
            db_profile.row_count = profile_data["total_rows"]
            db_profile.column_count = profile_data["column_count"]
            db_profile.duplicate_rows = profile_data.get("duplicate_rows", 0)
            db_profile.quality_score = profile_data.get("quality_score", 100)
            db_profile.profile_metadata = profile_data.get("columns", {})
            db_profile.warnings = profile_data.get("warnings", [])

        # 2. Synchronize ColumnSemanticMappings
        map_stmt = select(ColumnSemanticMapping).where(
            ColumnSemanticMapping.dataset_version_id == version.id
        )
        map_res = await db.execute(map_stmt)
        existing_mappings = {m.column_name: m for m in map_res.scalars().all()}

        columns_profile = profile_data.get("columns", {})
        saved_mappings: list[ColumnSemanticMapping] = []

        for col_name, cinfo in columns_profile.items():
            existing = existing_mappings.get(col_name)

            # Rule: NEVER overwrite USER_CONFIRMED mappings
            if existing and existing.mapping_status == "USER_CONFIRMED":
                saved_mappings.append(existing)
                continue

            if existing:
                # Update existing system or AI suggested mapping
                existing.physical_type = cinfo.get("physical_type", "VARCHAR")
                existing.logical_type = cinfo.get("logical_type", "string")
                existing.semantic_type = cinfo.get("semantic_type", "text")
                existing.aggregation_method = cinfo.get("aggregation_method", "NONE")
                existing.format_string = cinfo.get("format_string")
                existing.is_dimension = cinfo.get("is_dimension", True)
                existing.is_measure = cinfo.get("is_measure", False)
                existing.is_primary_key = cinfo.get("is_primary_key", False)
                existing.is_foreign_key = cinfo.get("is_foreign_key", False)
                existing.confidence_score = cinfo.get("confidence_score", 1.0)
                saved_mappings.append(existing)
            else:
                new_map = ColumnSemanticMapping(
                    dataset_version_id=version.id,
                    dataset_id=dataset.id,
                    column_name=col_name,
                    business_name=cinfo.get("business_name", col_name.title()),
                    description=f"Inferred {cinfo.get('semantic_type', 'attribute')} column.",
                    semantic_type=cinfo.get("semantic_type", "text"),
                    logical_type=cinfo.get("logical_type", "string"),
                    physical_type=cinfo.get("physical_type", "VARCHAR"),
                    aggregation_method=cinfo.get("aggregation_method", "NONE"),
                    format_string=cinfo.get("format_string"),
                    is_dimension=cinfo.get("is_dimension", True),
                    is_measure=cinfo.get("is_measure", False),
                    is_primary_key=cinfo.get("is_primary_key", False),
                    is_foreign_key=cinfo.get("is_foreign_key", False),
                    mapping_status="SYSTEM_INFERRED",
                    confidence_score=cinfo.get("confidence_score", 1.0),
                )
                db.add(new_map)
                saved_mappings.append(new_map)

        await db.flush()
        return db_profile, saved_mappings

    @classmethod
    async def inherit_mappings_for_new_version(
        cls,
        dataset_id: uuid.UUID,
        prior_version_id: uuid.UUID,
        new_version_id: uuid.UUID,
        db: AsyncSession,
    ) -> int:
        """
        Transfers existing user-confirmed and system mappings from a prior version
        to a newly materialized dataset version, preserving historical definitions.
        """
        # Fetch previous mappings
        stmt = select(ColumnSemanticMapping).where(
            ColumnSemanticMapping.dataset_version_id == prior_version_id
        )
        res = await db.execute(stmt)
        prior_mappings = res.scalars().all()

        inherited_count = 0
        for m in prior_mappings:
            new_map = ColumnSemanticMapping(
                dataset_version_id=new_version_id,
                dataset_id=dataset_id,
                column_name=m.column_name,
                business_name=m.business_name,
                description=m.description,
                semantic_type=m.semantic_type,
                logical_type=m.logical_type,
                physical_type=m.physical_type,
                aggregation_method=m.aggregation_method,
                format_string=m.format_string,
                is_dimension=m.is_dimension,
                is_measure=m.is_measure,
                is_primary_key=m.is_primary_key,
                is_foreign_key=m.is_foreign_key,
                mapping_status=m.mapping_status,
                confidence_score=m.confidence_score,
                confirmed_by_user_id=m.confirmed_by_user_id,
            )
            db.add(new_map)
            inherited_count += 1

        await db.flush()
        logger.info(
            "Inherited %d column mappings from version %s to %s",
            inherited_count, prior_version_id, new_version_id,
        )
        return inherited_count

    @classmethod
    async def update_column_mapping(
        cls,
        version_id: uuid.UUID,
        column_name: str,
        updates: dict[str, Any],
        user_id: uuid.UUID | None,
        db: AsyncSession,
    ) -> ColumnSemanticMapping:
        """
        Allows users to confirm or edit business name, semantic type,
        aggregation, and dimension/measure flags.
        """
        stmt = select(ColumnSemanticMapping).where(
            ColumnSemanticMapping.dataset_version_id == version_id,
            ColumnSemanticMapping.column_name == column_name,
        )
        res = await db.execute(stmt)
        mapping = res.scalar_one_or_none()
        if not mapping:
            raise DataLensException(
                f"Column '{column_name}' mapping not found in version '{version_id}'.",
                code="NOT_FOUND",
            )

        if "business_name" in updates:
            mapping.business_name = updates["business_name"].strip()
        if "description" in updates:
            mapping.description = updates["description"]
        if "semantic_type" in updates:
            mapping.semantic_type = updates["semantic_type"]
        if "aggregation_method" in updates:
            mapping.aggregation_method = updates["aggregation_method"].upper()
        if "format_string" in updates:
            mapping.format_string = updates["format_string"]
        if "is_dimension" in updates:
            mapping.is_dimension = bool(updates["is_dimension"])
        if "is_measure" in updates:
            mapping.is_measure = bool(updates["is_measure"])
        mapping.mapping_status = updates.get("mapping_status", "USER_CONFIRMED")

        mapping.confirmed_by_user_id = user_id
        await db.flush()
        return mapping
