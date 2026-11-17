import json
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.logging import logger
from app.models.conversational_analytics import (
    NLAMessage,
    NLASession,
    SavedAnalysis,
)
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.services.ai.factory import AIProviderFactory
from app.services.ai.intent_classifier import (
    ConversationalResponseBuilder,
    ConversationIntent,
    IntentClassifier,
)
from app.services.nla.compiler import NLASafeQueryCompiler
from app.services.nla.executor import NLAQueryExecutor
from app.services.nla.planner import NLAQueryPlanner
from app.services.nla.schemas import (
    NLAQueryRequest,
    SavedAnalysisCreateRequest,
)
from app.services.nla.verifier import NLAEvidenceVerifier
from app.services.nla.visualizer import NLAVisualizer


class NLASessionService:
    """
    Coordinates conversational sessions, query planning, DuckDB execution,
    verified narrative generation, and session memory updates.
    """

    @classmethod
    async def _resolve_parquet_paths(
        cls, dataset_id: uuid.UUID, version_id: uuid.UUID | None, db: AsyncSession
    ) -> tuple[Dataset, DatasetVersion, list[Path]]:
        stmt = (
            select(Dataset)
            .options(selectinload(Dataset.current_version))
            .where(Dataset.id == dataset_id, Dataset.is_archived.is_(False))
        )
        dataset = (await db.execute(stmt)).scalar_one_or_none()
        if not dataset:
            raise DataLensException(f"Dataset '{dataset_id}' not found.", code="NOT_FOUND")

        target_ver_id = version_id or dataset.current_version_id
        if not target_ver_id:
            raise DataLensException("Dataset has no active version to query.", code="NOT_FOUND")

        ver_stmt = select(DatasetVersion).where(
            DatasetVersion.id == target_ver_id, DatasetVersion.dataset_id == dataset.id
        )
        version = (await db.execute(ver_stmt)).scalar_one_or_none()
        if not version:
            raise DataLensException("Dataset version not found.", code="NOT_FOUND")

        storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
        manifest_path = storage_root / version.storage_key
        if not manifest_path.is_file():
            raise DataLensException("Dataset manifest not found on disk.", code="STORAGE_NOT_FOUND")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parquet_paths = [storage_root / p for p in manifest.get("parts", [])]

        return dataset, version, parquet_paths

    @classmethod
    def _get_suggested_questions_for_schema(
        cls, dataset_name: str, col_names: list[str]
    ) -> list[str]:
        cols_lower = [c.lower() for c in col_names]
        has_rev = any(k in cols_lower for k in ("revenue", "sales", "amount", "price", "cost", "total"))
        has_prod = any(k in cols_lower for k in ("product", "item", "plan", "sku", "facility", "category"))
        has_reg = any(k in cols_lower for k in ("region", "country", "city", "state", "location", "territory"))
        has_date = any(k in cols_lower for k in ("date", "order_date", "month", "created_at", "timestamp"))

        qs: list[str] = []
        if has_prod and has_rev:
            qs.append("Which product generated the highest revenue?")
        if has_date and has_rev:
            qs.append("Show monthly revenue trend")
        if has_reg and has_rev:
            qs.append("Compare regional performance")
        if not qs and has_rev:
            qs.append("What is the total revenue?")
        if not qs and has_prod:
            qs.append("Breakdown by top products")
        if not qs:
            qs.extend([
                f"Give me key insights for {dataset_name}",
                "Show dataset summary and distribution",
            ])
        return qs[:3]

    @classmethod
    async def execute_nl_query(
        cls,
        req: NLAQueryRequest,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> NLAMessage:
        """
        Processes natural language query end-to-end and returns persisted NLAMessage response.
        """
        start_time = time.perf_counter()

        # 1. Resolve Dataset, Version & Parquet Storage
        dataset, version, primary_parquet = await cls._resolve_parquet_paths(
            req.dataset_id, req.version_id, db
        )

        # 2. Resolve or Create Session
        session: NLASession | None = None
        if req.session_id:
            s_stmt = select(NLASession).where(
                NLASession.id == req.session_id,
                NLASession.workspace_id == workspace_id,
            )
            session = (await db.execute(s_stmt)).scalar_one_or_none()

        if not session:
            title_clean = req.question[:40].strip() + ("..." if len(req.question) > 40 else "")
            session = NLASession(
                workspace_id=workspace_id,
                user_id=user_id,
                title=title_clean,
                dataset_id=dataset.id,
                dataset_version_id=version.id,
                active_context={},
            )
            db.add(session)
            await db.flush()

        # 3. Record User Message
        user_msg = NLAMessage(
            session_id=session.id,
            sender="user",
            content=req.question,
        )
        db.add(user_msg)
        await db.flush()

        # 3.5 Intent Classification Layer
        columns_meta: list[dict[str, Any]] = []
        try:
            storage_root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
            manifest_path = storage_root / version.storage_key
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                columns_meta = manifest.get("columns", [])
        except Exception:
            pass
        col_names = [c["name"] for c in columns_meta] if columns_meta else []

        intent = IntentClassifier.classify(
            question=req.question,
            conversation_history=[{"role": "user", "content": req.question}],
            active_context=session.active_context,
            columns=col_names,
        )

        # Handle Conversational & Non-Analytical Intents (Zero DuckDB query execution)
        if intent in (
            ConversationIntent.GREETING,
            ConversationIntent.CASUAL_CONVERSATION,
            ConversationIntent.CAPABILITY_QUERY,
            ConversationIntent.UNSUPPORTED_REQUEST,
            ConversationIntent.DATA_EXPLANATION,
        ):
            suggested_qs = cls._get_suggested_questions_for_schema(dataset.name, col_names)

            conv_res = await ConversationalResponseBuilder.build_conversational_response_async(
                question=req.question,
                intent=intent,
                dataset_name=dataset.name,
                row_count=version.row_count,
                columns=columns_meta,
                conversation_history=[{"role": "user", "content": req.question}],
                previous_result=session.active_context,
                suggested_questions=suggested_qs,
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            assistant_msg = NLAMessage(
                session_id=session.id,
                sender="assistant",
                content=conv_res["content"],
                direct_answer=conv_res["direct_answer"],
                intent=conv_res["intent"],
                plan_json={"suggested_follow_ups": conv_res.get("suggested_follow_ups", [])},
                results_summary=None,
                metric_cards=[],
                chart_data=None,
                table_data=None,
                evidence_items=[],
                needs_clarification=False,
                clarification_options=[],
                provider_used="conversational_router",
                execution_duration_ms=duration_ms,
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return assistant_msg

        # 4. Formulate Analytical Plan
        plan, metric_formula = await NLAQueryPlanner.formulate_plan(
            question=req.question,
            workspace_id=workspace_id,
            dataset_id=dataset.id,
            dataset_version_id=version.id,
            db=db,
            active_context=session.active_context,
        )

        # Append manual request filters if supplied
        if req.filters:
            plan.filters.extend(req.filters)

        # 5. Handle Ambiguity / Clarification
        if plan.needs_clarification:
            assistant_msg = NLAMessage(
                session_id=session.id,
                sender="assistant",
                content=plan.clarification_message or "Could you clarify your question?",
                direct_answer=plan.clarification_message,
                intent="clarification",
                plan_json=plan.model_dump(),
                needs_clarification=True,
                clarification_options=plan.clarification_options,
                provider_used="deterministic",
                execution_duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return assistant_msg

        # 6. Secondary Dataset Parquet resolution if joining
        secondary_parquet: list[Path] | None = None
        if plan.secondary_dataset_id:
            try:
                _, _, secondary_parquet = await cls._resolve_parquet_paths(
                    plan.secondary_dataset_id, None, db
                )
            except Exception as ex:
                logger.warning("Could not resolve secondary join dataset: %s", ex)
                plan.secondary_dataset_id = None

        # 7. Compile Plan to SQL
        sql_query, params = NLASafeQueryCompiler.compile_plan_to_sql(
            plan=plan,
            primary_parquet_files=primary_parquet,
            secondary_parquet_files=secondary_parquet,
            metric_formula=metric_formula,
        )

        # 8. Execute DuckDB Query
        exec_result = NLAQueryExecutor.execute_query(sql_query, params, plan)

        # 9. Recommend Visualization
        metric_label = plan.metric_name or "Metric"
        chart_data, table_data = NLAVisualizer.recommend_visualization(
            plan=plan, result_data=exec_result, metric_label=metric_label
        )

        # 10. Generate Grounded Narrative via AI Provider Router
        router = AIProviderFactory.get_router()
        provider_name = "deterministic"
        raw_explanation = ""

        try:
            exp_text, prov = await router.explain_results(
                query=req.question,
                sql_query=sql_query,
                results_summary=exec_result,
                schema_context={"dataset_name": dataset.name, "rows": exec_result.get("rows", [])[:5]},
                dataset_sensitivity=getattr(dataset, "sensitivity_tier", "INTERNAL"),
            )
            raw_explanation = exp_text
            provider_name = prov
        except Exception as ex:
            logger.warning("AI explanation generation fallback: %s", ex)
            provider_name = "deterministic"

        # 11. Evidence Verification & Grounding
        is_curr = any(k in metric_label.lower() for k in ("revenue", "sales", "price", "amount", "cost"))
        verified_evidence = NLAEvidenceVerifier.synthesize_verified_evidence(
            plan=plan,
            result_data=exec_result,
            raw_explanation=raw_explanation,
            metric_name=metric_label,
            dataset_name=dataset.name,
            version_number=version.version_number,
            is_currency=is_curr,
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # 12. Update Session Active Context
        session.active_context = {
            "active_metric_name": metric_label,
            "active_dimensions": plan.group_by_columns,
            "active_filters": [f.model_dump() for f in plan.filters],
            "time_granularity": plan.time_granularity,
            "last_intent": plan.intent,
        }

        # 13. Persist Assistant Response
        assistant_msg = NLAMessage(
            session_id=session.id,
            sender="assistant",
            content=verified_evidence["ai_explanation"],
            direct_answer=verified_evidence["direct_answer"],
            intent=plan.intent,
            plan_json=plan.model_dump(),
            results_summary=exec_result,
            metric_cards=verified_evidence["metric_cards"],
            chart_data=chart_data,
            table_data=table_data,
            evidence_items=verified_evidence["evidence_items"],
            needs_clarification=False,
            provider_used=provider_name,
            execution_duration_ms=duration_ms,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        return assistant_msg

    @classmethod
    async def create_saved_analysis(
        cls,
        req: SavedAnalysisCreateRequest,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> SavedAnalysis:
        saved = SavedAnalysis(
            workspace_id=workspace_id,
            user_id=user_id,
            title=req.title.strip(),
            description=req.description,
            question=req.question.strip(),
            dataset_id=req.dataset_id,
            dataset_version_id=req.dataset_version_id,
            plan_json=req.plan_json,
            results_summary=req.results_summary,
            chart_config=req.chart_config,
            tags=req.tags,
        )
        db.add(saved)
        await db.commit()
        await db.refresh(saved)
        return saved
