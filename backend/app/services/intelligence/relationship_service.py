import re
import uuid
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataLensException
from app.core.logging import logger
from app.models.dataset import Dataset
from app.models.intelligence import ColumnSemanticMapping, DatasetRelationship


class RelationshipDiscoveryEngine:
    """
    Intelligent cross-dataset relationship discovery within workspace boundaries.
    Analyzes column naming, semantic types, key uniqueness, and sample value overlap via DuckDB.
    """

    @classmethod
    def _sanitize(cls, name: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", name):
            raise DataLensException(f"Invalid column identifier: '{name}'.", code="INVALID_COLUMN")
        return f'"{name}"'

    @classmethod
    async def discover_workspace_relationships(
        cls,
        workspace_id: uuid.UUID,
        db: AsyncSession,
        parquet_resolver: Any = None,
    ) -> list[DatasetRelationship]:
        """
        Scans all datasets in the workspace, finds matching key/identifier columns,
        calculates overlap and cardinality, and stores discovered relationships.
        """
        # 1. Fetch all datasets in workspace with current version
        stmt = (
            select(Dataset)
            .where(Dataset.workspace_id == workspace_id, Dataset.status == "ready")
        )
        res = await db.execute(stmt)
        datasets = res.scalars().all()

        if len(datasets) < 2:
            return []

        # 2. Fetch column semantic mappings for current versions
        version_ids = [d.current_version_id for d in datasets if d.current_version_id]
        if not version_ids:
            return []

        map_stmt = select(ColumnSemanticMapping).where(
            ColumnSemanticMapping.dataset_version_id.in_(version_ids)
        )
        map_res = await db.execute(map_stmt)
        all_mappings = map_res.scalars().all()

        # Group mappings by dataset_id
        ds_mappings: dict[uuid.UUID, list[ColumnSemanticMapping]] = {}
        for m in all_mappings:
            ds_mappings.setdefault(m.dataset_id, []).append(m)

        # 3. Existing relationships check
        rel_stmt = select(DatasetRelationship).where(
            DatasetRelationship.workspace_id == workspace_id
        )
        rel_res = await db.execute(rel_stmt)
        existing_rels = {
            (r.source_dataset_id, r.source_column, r.target_dataset_id, r.target_column): r
            for r in rel_res.scalars().all()
        }

        discovered: list[DatasetRelationship] = []

        # Compare pairwise datasets
        for i, src_ds in enumerate(datasets):
            src_maps = ds_mappings.get(src_ds.id, [])
            for j, tgt_ds in enumerate(datasets):
                if i == j:
                    continue  # do not self-join here
                tgt_maps = ds_mappings.get(tgt_ds.id, [])

                for s_col in src_maps:
                    # Target candidate columns
                    for t_col in tgt_maps:
                        match_score, match_reasons = cls._evaluate_candidate_pair(
                            src_ds, s_col, tgt_ds, t_col
                        )
                        if match_score < 0.6:
                            continue

                        # Determine Cardinality
                        cardinality = cls._infer_cardinality(s_col, t_col)

                        # Join warning
                        join_warning = None
                        if cardinality == "MANY_TO_MANY":
                            join_warning = (
                                "Many-to-many relationship detected. Joining on these columns "
                                "may cause row multiplication and distort metric sums."
                            )

                        evidence = {
                            "name_match": s_col.column_name.lower() == t_col.column_name.lower(),
                            "semantic_match": s_col.semantic_type == t_col.semantic_type,
                            "match_reasons": match_reasons,
                            "source_is_pk": s_col.is_primary_key,
                            "target_is_pk": t_col.is_primary_key,
                        }

                        key = (src_ds.id, s_col.column_name, tgt_ds.id, t_col.column_name)
                        reverse_key = (tgt_ds.id, t_col.column_name, src_ds.id, s_col.column_name)

                        if key in existing_rels or reverse_key in existing_rels:
                            continue

                        new_rel = DatasetRelationship(
                            workspace_id=workspace_id,
                            source_dataset_id=src_ds.id,
                            source_version_id=src_ds.current_version_id,
                            source_column=s_col.column_name,
                            target_dataset_id=tgt_ds.id,
                            target_version_id=tgt_ds.current_version_id,
                            target_column=t_col.column_name,
                            relationship_type=cardinality,
                            confidence_score=round(match_score, 2),
                            status="SUGGESTED",
                            evidence=evidence,
                            join_warning=join_warning,
                        )
                        db.add(new_rel)
                        discovered.append(new_rel)
                        existing_rels[key] = new_rel

        if discovered:
            await db.flush()
        return discovered

    @classmethod
    def _evaluate_candidate_pair(
        cls,
        src_ds: Dataset,
        s_col: ColumnSemanticMapping,
        tgt_ds: Dataset,
        t_col: ColumnSemanticMapping,
    ) -> tuple[float, list[str]]:
        """
        Evaluates potential join relationship between two columns across datasets.
        """
        score = 0.0
        reasons: list[str] = []

        s_name = s_col.column_name.lower()
        t_name = t_col.column_name.lower()

        # 1. Exact name match
        if s_name == t_name:
            if s_name.endswith(("_id", "_key", "_code", "id")):
                score += 0.50
                reasons.append("Exact identifier column name match")
            else:
                score += 0.30
                reasons.append("Exact column name match")
        elif s_name.replace("_", "") == t_name.replace("_", ""):
            score += 0.40
            reasons.append("Normalized column name match")
        elif t_name in ("id", f"{tgt_ds.name.lower()}_id", f"{tgt_ds.original_filename.split('.')[0].lower()}_id"):
            if s_name == f"{tgt_ds.name.lower()}_id" or s_name.endswith(f"_{t_name}"):
                score += 0.55
                reasons.append(f"Foreign key naming pattern '{s_name}' matches target '{t_name}'")

        # 2. Semantic type match
        if s_col.semantic_type == t_col.semantic_type and s_col.semantic_type not in ("text", "numeric"):
            score += 0.30
            reasons.append(f"Matching semantic type: {s_col.semantic_type}")

        # 3. Primary Key & Foreign Key affinity
        if t_col.is_primary_key and (s_col.is_foreign_key or s_name.endswith("_id")):
            score += 0.25
            reasons.append("Target column is primary key and source column is foreign key")
        elif s_col.is_primary_key and t_col.is_primary_key:
            score += 0.20
            reasons.append("Both columns are unique primary keys")

        # 4. Data type compatibility
        if s_col.logical_type == t_col.logical_type:
            score += 0.10
        else:
            score -= 0.30
            reasons.append(f"Type mismatch ({s_col.logical_type} vs {t_col.logical_type})")

        return min(1.0, max(0.0, score)), reasons

    @classmethod
    def _infer_cardinality(
        cls, s_col: ColumnSemanticMapping, t_col: ColumnSemanticMapping
    ) -> str:
        s_unique = s_col.is_primary_key
        t_unique = t_col.is_primary_key

        if s_unique and t_unique:
            return "ONE_TO_ONE"
        if not s_unique and t_unique:
            return "MANY_TO_ONE"
        if s_unique and not t_unique:
            return "ONE_TO_MANY"
        return "MANY_TO_MANY"

    @classmethod
    def calculate_value_overlap(
        cls,
        src_parquet: list[Path],
        src_col: str,
        tgt_parquet: list[Path],
        tgt_col: str,
    ) -> dict[str, Any]:
        """
        Bounded DuckDB execution to check referential coverage between two datasets.
        """
        con = duckdb.connect(":memory:")
        try:
            s_paths = ", ".join(f"'{str(p.resolve()).replace('\\', '/')}'" for p in src_parquet if p.is_file())
            t_paths = ", ".join(f"'{str(p.resolve()).replace('\\', '/')}'" for p in tgt_parquet if p.is_file())
            if not s_paths or not t_paths:
                return {"overlap_ratio": 0.0, "common_count": 0}

            safe_s = cls._sanitize(src_col)
            safe_t = cls._sanitize(tgt_col)

            query = f"""
                WITH s AS (
                    SELECT DISTINCT CAST({safe_s} AS VARCHAR) AS val
                    FROM read_parquet([{s_paths}])
                    WHERE {safe_s} IS NOT NULL
                ),
                t AS (
                    SELECT DISTINCT CAST({safe_t} AS VARCHAR) AS val
                    FROM read_parquet([{t_paths}])
                    WHERE {safe_t} IS NOT NULL
                )
                SELECT
                    (SELECT COUNT(*) FROM s) AS src_distinct,
                    (SELECT COUNT(*) FROM t) AS tgt_distinct,
                    (SELECT COUNT(*) FROM s INNER JOIN t ON s.val = t.val) AS common_count
            """
            res = con.execute(query).fetchone()
            if not res:
                return {"overlap_ratio": 0.0, "common_count": 0}

            src_dist, tgt_dist, common = res
            overlap = round(common / src_dist, 4) if src_dist > 0 else 0.0
            return {
                "source_distinct": src_dist,
                "target_distinct": tgt_dist,
                "common_count": common,
                "overlap_ratio": overlap,
            }
        except Exception as ex:
            logger.warning("Error computing value overlap: %s", ex)
            return {"overlap_ratio": 0.0, "common_count": 0, "error": str(ex)}
        finally:
            con.close()
