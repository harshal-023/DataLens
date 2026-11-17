import hashlib
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.models.business_analyst import (
    BusinessInsight,
    InsightAssessment,
    InsightAssignment,
    InsightComment,
    InsightEvidence,
    InsightGenerationRun,
)
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.intelligence import (
    ColumnSemanticMapping,
    MetricDefinition,
)
from app.services.business_analyst.anomaly_engine import AnomalyEngine
from app.services.business_analyst.explanation_engine import ExplanationEngine
from app.services.business_analyst.opportunity_engine import OpportunityEngine
from app.services.business_analyst.risk_engine import RiskEngine
from app.services.business_analyst.trend_engine import TrendEngine
from app.services.nla.compiler import NLASafeQueryCompiler
from app.services.nla.executor import NLAQueryExecutor
from app.services.nla.schemas import NLAQueryPlan

logger = logging.getLogger("datalens.analyst.insight_engine")


class BusinessInsightEngine:
    """
    Central Autonomous Business Insight Engine.
    Executes proactive analytical sweeps across datasets, detecting trends,
    anomalies, risks, and opportunities with multi-factor prioritization and lifecycle auditing.
    """

    @classmethod
    def _compute_fingerprint(
        cls,
        version_id: uuid.UUID,
        category: str,
        metric: str,
        segment: str | None,
        finding_type: str,
    ) -> str:
        raw_key = f"{version_id}_{category}_{metric}_{segment or 'overall'}_{finding_type}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:32]

    @classmethod
    async def run_autonomous_analysis(
        cls,
        workspace_id: uuid.UUID,
        dataset_id: uuid.UUID,
        db: AsyncSession,
        version_id: uuid.UUID | None = None,
        trigger_type: str = "manual",
        ai_provider: str | None = None,
    ) -> InsightGenerationRun:
        """
        Executes a complete proactive analytical sweep over a dataset version.
        """
        start_time = time.perf_counter()

        # 1. Fetch Dataset & Target Version
        stmt = select(Dataset).options(selectinload(Dataset.versions)).where(
            Dataset.id == dataset_id,
            Dataset.workspace_id == workspace_id,
        )
        res = await db.execute(stmt)
        dataset = res.scalar_one_or_none()
        if not dataset:
            raise DataLensException("Dataset not found in workspace.", code="NOT_FOUND")

        target_version: DatasetVersion | None = None
        if version_id:
            target_version = next((v for v in dataset.versions if v.id == version_id), None)
        else:
            sorted_versions = sorted(dataset.versions, key=lambda v: v.created_at, reverse=True)
            target_version = sorted_versions[0] if sorted_versions else None

        if not target_version:
            raise DataLensException("Dataset has no valid version available for analysis.", code="NO_VERSION")

        storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
        parquet_files = []
        if getattr(target_version, "storage_key", None):
            cleaned_key = str(target_version.storage_key).strip().replace("\\", "/")
            direct_path = Path(cleaned_key)
            if direct_path.is_file():
                manifest_or_parquet = direct_path
            else:
                manifest_or_parquet = storage_root / cleaned_key

            if manifest_or_parquet.is_file():
                if cleaned_key.endswith(".json"):
                    try:
                        manifest = json.loads(manifest_or_parquet.read_text(encoding="utf-8"))
                        for p in manifest.get("parts", []):
                            part_clean = str(p).strip().replace("\\", "/")
                            part_path = Path(part_clean) if Path(part_clean).is_file() else (storage_root / part_clean)
                            if part_path.is_file():
                                parquet_files.append(part_path)
                    except Exception:
                        pass
                elif cleaned_key.endswith(".parquet"):
                    parquet_files = [manifest_or_parquet]

        if not parquet_files:
            for p in (getattr(target_version, "storage_paths", None) or []):
                p_clean = str(p).strip().replace("\\", "/")
                cand = Path(p_clean) if Path(p_clean).is_file() else (storage_root / p_clean)
                if cand.is_file():
                    parquet_files.append(cand)

        if not parquet_files:
            candidate = storage_root / "datasets" / str(dataset.id) / f"{target_version.id}.parquet"
            if candidate.is_file():
                parquet_files = [candidate]

        if not parquet_files:
            dataset_dir = storage_root / "datasets" / str(dataset.id)
            if dataset_dir.is_dir():
                found_parquets = list(dataset_dir.glob("*.parquet"))
                if found_parquets:
                    parquet_files = [found_parquets[0]]

        if not parquet_files:
            raise DataLensException(
                f"No analytical data files (parquet) found for dataset version {target_version.id}. Please re-upload or refresh the dataset.",
                code="STORAGE_FILE_MISSING",
            )

        # Initialize Generation Run Record
        run_record = InsightGenerationRun(
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            dataset_version_id=target_version.id,
            trigger_type=trigger_type,
            status="running",
            insights_generated_count=0,
            execution_duration_ms=0,
        )
        db.add(run_record)
        await db.flush()

        try:
            # 2. Fetch Semantic Mappings & Approved Metrics
            col_stmt = select(ColumnSemanticMapping).where(
                ColumnSemanticMapping.dataset_version_id == target_version.id
            )
            col_res = await db.execute(col_stmt)
            mappings = col_res.scalars().all()

            met_stmt = select(MetricDefinition).where(
                MetricDefinition.workspace_id == workspace_id,
                (MetricDefinition.dataset_id == dataset_id) | (MetricDefinition.dataset_id.is_(None)),
                MetricDefinition.approval_status == "APPROVED",
            )
            met_res = await db.execute(met_stmt)
            metrics = met_res.scalars().all()

            # Identify key dimensions and measures
            date_col = next((m.column_name for m in mappings if m.semantic_type in ("date", "timestamp") or m.logical_type in ("date", "datetime")), None)
            dim_cols = [m.column_name for m in mappings if m.is_dimension and not m.is_primary_key]
            measure_cols = [m.column_name for m in mappings if m.is_measure]

            if (not date_col or not measure_cols or not dim_cols) and target_version.schema_metadata:
                cols = target_version.schema_metadata.get("columns", [])
                if not date_col:
                    date_col = next((c["name"] for c in cols if any(k in c.get("inferred_type", "").lower() for k in ("date", "time", "timestamp")) or c["name"].lower() in ("date", "timestamp", "order_date", "created_at", "trans_date", "datetime")), None)
                if not measure_cols:
                    measure_cols = [c["name"] for c in cols if any(k in c.get("inferred_type", "").lower() for k in ("int", "float", "num", "double", "decimal", "real"))]
                if not dim_cols:
                    dim_cols = [c["name"] for c in cols if c["name"] != date_col and c["name"] not in measure_cols]
            
            raw_findings: list[dict[str, Any]] = []

            # Execute analyses only if Parquet files are present
            if parquet_files:
                primary_metric_col = measure_cols[0] if measure_cols else "id"
                metric_display = metrics[0].name if metrics else primary_metric_col.replace("_", " ").title()

                # --- Analysis A: Trends & Time-Series ---
                if date_col:
                    trend_plan = NLAQueryPlan(
                        intent="time_series",
                        metric_column=primary_metric_col,
                        aggregation="SUM",
                        date_column=date_col,
                        time_granularity="monthly",
                        limit=50,
                    )
                    sql, params = NLASafeQueryCompiler.compile_plan_to_sql(trend_plan, parquet_files)
                    ts_res = NLAQueryExecutor.execute_query(sql, params)
                    ts_rows = ts_res.get("rows", [])

                    # Detect trends
                    trends = TrendEngine.evaluate_metric_trend(ts_rows, metric_name=metric_display)
                    for t in trends:
                        t["category"] = "trend"
                        t["affected_metric"] = metric_display
                        t["affected_dimension"] = date_col
                        raw_findings.append(t)

                    # Detect anomalies over time series
                    anomalies = AnomalyEngine.evaluate_series_anomalies(
                        ts_rows, metric_name=metric_display, dimension_name="period"
                    )
                    for a in anomalies:
                        a["category"] = "anomaly"
                        raw_findings.append(a)

                # --- Analysis B: Categorical Breakdowns, Risks & Opportunities ---
                for dim in dim_cols[:3]:  # Top dimensions (e.g. region, product, customer)
                    cat_plan = NLAQueryPlan(
                        intent="group_by",
                        metric_column=primary_metric_col,
                        aggregation="SUM",
                        group_by_columns=[dim],
                        limit=25,
                    )
                    sql, params = NLASafeQueryCompiler.compile_plan_to_sql(cat_plan, parquet_files)
                    cat_res = NLAQueryExecutor.execute_query(sql, params)
                    cat_rows = cat_res.get("rows", [])

                    # 1. Concentration risks
                    risks = RiskEngine.evaluate_concentration_risk(
                        cat_rows, dimension_name=dim, metric_name=metric_display
                    )
                    raw_findings.extend(risks)

                    # 2. Growth opportunities
                    opps = OpportunityEngine.evaluate_growth_opportunities(
                        cat_rows, dimension_name=dim, metric_name=metric_display
                    )
                    raw_findings.extend(opps)

            # 3. Process & Ground Findings with AI / Verification
            created_count = 0
            for finding in raw_findings:
                cat = finding.get("category", "performance")
                metric = finding.get("affected_metric", "Metric")
                dim = finding.get("affected_dimension")
                seg = finding.get("affected_segment")
                f_type = finding.get("type", "general")
                severity = finding.get("severity", "MEDIUM")

                fingerprint = cls._compute_fingerprint(target_version.id, cat, metric, seg, f_type)

                # Deduplication check: check if insight with same fingerprint already exists for this version
                exist_stmt = select(BusinessInsight).where(
                    BusinessInsight.dataset_version_id == target_version.id,
                    BusinessInsight.fingerprint == fingerprint,
                )
                exist_res = await db.execute(exist_stmt)
                existing = exist_res.scalar_one_or_none()

                # Generate AI grounded explanation
                explanation_bundle = await ExplanationEngine.generate_explanation(
                    finding,
                    workspace_id=workspace_id,
                    preferred_provider=ai_provider,
                )

                if existing:
                    # Update existing insight with fresh run details
                    existing.generation_run_id = run_record.id
                    existing.score = finding.get("score", existing.score)
                    existing.detailed_explanation = explanation_bundle["detailed_explanation"]
                    continue

                # Create new insight
                insight = BusinessInsight(
                    workspace_id=workspace_id,
                    dataset_id=dataset_id,
                    dataset_version_id=target_version.id,
                    generation_run_id=run_record.id,
                    title=finding.get("title", "Analytical Finding"),
                    category=cat,
                    severity=severity,
                    status="NEW",
                    summary=finding.get("summary", ""),
                    detailed_explanation=explanation_bundle["detailed_explanation"],
                    affected_metric=metric,
                    affected_dimension=dim,
                    affected_segment=seg,
                    score=finding.get("score", 0.7),
                    priority_reason=finding.get("priority_reason"),
                    recommended_action=explanation_bundle["recommended_action"],
                    suggested_investigation=explanation_bundle["suggested_investigation"],
                    ai_provider=explanation_bundle["ai_provider"],
                    fingerprint=fingerprint,
                )
                db.add(insight)
                await db.flush()

                # Add supporting evidence item
                evidence = InsightEvidence(
                    insight_id=insight.id,
                    evidence_type=f_type,
                    metric_name=metric,
                    baseline_value=finding.get("baseline_value"),
                    observed_value=finding.get("observed_value", "N/A"),
                    deviation_pct=finding.get("deviation_pct"),
                    supporting_data=finding.get("supporting_data"),
                    calculation_formula=finding.get("calculation_formula"),
                    verified=True,
                )
                db.add(evidence)
                created_count += 1

            # 4. Finalize Run Record
            duration = int((time.perf_counter() - start_time) * 1000)
            run_record.status = "completed"
            run_record.insights_generated_count = created_count
            run_record.execution_duration_ms = duration
            run_record.completed_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(run_record)
            return run_record

        except Exception as e:
            await db.rollback()
            run_record.status = "failed"
            run_record.error_message = str(e)
            run_record.execution_duration_ms = int((time.perf_counter() - start_time) * 1000)
            run_record.completed_at = datetime.now(UTC)
            db.add(run_record)
            await db.commit()
            logger.error(f"Insight generation failed: {e}", exc_info=True)
            raise

    @classmethod
    async def get_executive_overview(
        cls,
        workspace_id: uuid.UUID,
        db: AsyncSession,
        dataset_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Generates high-level executive business overview KPIs and priority findings.
        """
        base_query = select(BusinessInsight).where(BusinessInsight.workspace_id == workspace_id)
        if dataset_id:
            base_query = base_query.where(BusinessInsight.dataset_id == dataset_id)

        res = await db.execute(
            base_query.options(
                selectinload(BusinessInsight.evidence_items),
                selectinload(BusinessInsight.comments).selectinload(InsightComment.author),
            )
        )
        all_insights = res.scalars().all()

        critical_risks = [i for i in all_insights if i.category == "risk" and i.severity in ("CRITICAL", "HIGH")]
        opportunities = [i for i in all_insights if i.category == "opportunity"]
        anomalies = [i for i in all_insights if i.category == "anomaly"]

        # Top movements
        movements: list[dict[str, Any]] = []
        for i in all_insights[:5]:
            ev = i.evidence_items[0] if i.evidence_items else None
            movements.append({
                "title": i.title,
                "category": i.category,
                "severity": i.severity,
                "metric": i.affected_metric,
                "change": f"{ev.deviation_pct:+.1f}%" if ev and ev.deviation_pct is not None else None,
                "summary": i.summary,
            })

        return {
            "workspace_id": workspace_id,
            "dataset_id": dataset_id,
            "total_insights_count": len(all_insights),
            "critical_risks_count": len(critical_risks),
            "high_opportunities_count": len(opportunities),
            "anomalies_count": len(anomalies),
            "top_movements": movements,
            "critical_findings": critical_risks[:5],
            "positive_opportunities": opportunities[:5],
            "recent_changes": movements,
        }

    @classmethod
    async def update_status(
        cls,
        insight_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        new_status: str,
        db: AsyncSession,
        notes: str | None = None,
    ) -> BusinessInsight:
        """
        Updates insight lifecycle status and audits the assessment.
        """
        stmt = select(BusinessInsight).where(
            BusinessInsight.id == insight_id,
            BusinessInsight.workspace_id == workspace_id,
        )
        res = await db.execute(stmt)
        insight = res.scalar_one_or_none()
        if not insight:
            raise DataLensException("Business insight not found.", code="NOT_FOUND")

        old_status = insight.status
        insight.status = new_status
        now = datetime.now(UTC)

        if new_status == "ACKNOWLEDGED":
            insight.acknowledged_at = now
            insight.acknowledged_by_user_id = user_id
        elif new_status == "RESOLVED":
            insight.resolved_at = now
            insight.resolved_by_user_id = user_id

        # Record assessment audit entry
        assessment = InsightAssessment(
            insight_id=insight.id,
            assessment_type="manual_status_update",
            dataset_version_id=insight.dataset_version_id,
            status_change=f"{old_status} -> {new_status}",
            notes=notes or f"Status updated by user to {new_status}.",
            assessed_by_user_id=user_id,
        )
        db.add(assessment)
        await db.commit()
        await db.refresh(insight)
        return insight

    @classmethod
    async def assign_insight(
        cls,
        insight_id: uuid.UUID,
        workspace_id: uuid.UUID,
        assigned_by_user_id: uuid.UUID,
        assigned_to_user_id: uuid.UUID,
        db: AsyncSession,
        note: str | None = None,
    ) -> BusinessInsight:
        """
        Assigns an insight to a team member and logs the assignment event.
        """
        stmt = select(BusinessInsight).where(
            BusinessInsight.id == insight_id,
            BusinessInsight.workspace_id == workspace_id,
        )
        res = await db.execute(stmt)
        insight = res.scalar_one_or_none()
        if not insight:
            raise DataLensException("Business insight not found.", code="NOT_FOUND")

        prev_assigned = insight.assigned_to_user_id
        insight.assigned_to_user_id = assigned_to_user_id

        assignment = InsightAssignment(
            insight_id=insight.id,
            assigned_by_user_id=assigned_by_user_id,
            assigned_to_user_id=assigned_to_user_id,
            previous_assigned_to_user_id=prev_assigned,
            assignment_note=note,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(insight)
        return insight

    @classmethod
    async def add_comment(
        cls,
        insight_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        db: AsyncSession,
    ) -> InsightComment:
        """
        Adds a collaboration comment to a business insight.
        """
        stmt = select(BusinessInsight).where(
            BusinessInsight.id == insight_id,
            BusinessInsight.workspace_id == workspace_id,
        )
        res = await db.execute(stmt)
        insight = res.scalar_one_or_none()
        if not insight:
            raise DataLensException("Business insight not found.", code="NOT_FOUND")

        comment = InsightComment(
            insight_id=insight.id,
            user_id=user_id,
            content=content,
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment
