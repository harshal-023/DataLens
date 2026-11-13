import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.logging import logger
from app.models.analysis_run import AnalysisRun
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.services.ai.factory import AIProviderFactory
from app.services.ai.intent_classifier import (
    ConversationalResponseBuilder,
    ConversationIntent,
    IntentClassifier,
)
from app.services.ai.schemas import (
    AIAskResponse,
    AIChartData,
    AIEvidenceItem,
    AIMetricCard,
    AITableData,
    AnalyticalPlan,
)
from app.services.ai.validator import PlanValidator
from app.services.analytics.engine import AnalyticsEngine
from app.services.analytics.schemas import FilterCondition


class AIAnalyticsOrchestrator:
    """
    Coordinates AI analytical plan generation, schema validation, deterministic DuckDB execution,
    result persistence, and executive explanation generation.
    """

    @classmethod
    def _format_currency_or_num(cls, val: float, is_currency: bool = True) -> str:
        if abs(val) >= 1_000_000:
            formatted = f"{val / 1_000_000:.2f}M"
        elif abs(val) >= 1_000:
            formatted = f"{val / 1_000:.1f}K"
        else:
            formatted = f"{val:,.2f}"
        return f"${formatted}" if is_currency else formatted

    @classmethod
    def _get_suggested_questions(
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
    async def process_question(
        cls,
        question: str,
        dataset: Dataset,
        version: DatasetVersion,
        parquet_paths: list[Path],
        columns_meta: list[dict[str, Any]],
        user_id: uuid.UUID,
        db: AsyncSession,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AIAskResponse:
        start_time = time.perf_counter()
        router = AIProviderFactory.get_router()

        # Format conversation history if supplied
        formatted_history: list[dict[str, str]] | None = None
        if conversation_history:
            formatted_history = [
                (turn.model_dump() if hasattr(turn, "model_dump") else turn)
                for turn in conversation_history
            ]

        # 1. Intent Classification Layer (Distinguish Conversation from Data Analytics)
        col_names = [c["name"] for c in columns_meta]
        intent = IntentClassifier.classify(
            question=question,
            conversation_history=formatted_history,
            columns=col_names,
        )

        if intent in (
            ConversationIntent.GREETING,
            ConversationIntent.CASUAL_CONVERSATION,
            ConversationIntent.CAPABILITY_QUERY,
            ConversationIntent.UNSUPPORTED_REQUEST,
            ConversationIntent.DATA_EXPLANATION,
        ):
            suggested_qs = cls._get_suggested_questions(dataset.name, col_names)
            if intent == ConversationIntent.GREETING:
                conv_res = ConversationalResponseBuilder.build_greeting_response(
                    dataset_name=dataset.name,
                    row_count=version.row_count,
                    suggested_questions=suggested_qs,
                )
            elif intent == ConversationIntent.CASUAL_CONVERSATION:
                conv_res = ConversationalResponseBuilder.build_casual_response(question)
            elif intent == ConversationIntent.CAPABILITY_QUERY:
                conv_res = ConversationalResponseBuilder.build_capability_response(
                    dataset_name=dataset.name,
                    suggested_questions=suggested_qs,
                )
            elif intent == ConversationIntent.UNSUPPORTED_REQUEST:
                conv_res = ConversationalResponseBuilder.build_unsupported_response(question)
            else:  # DATA_EXPLANATION
                conv_res = ConversationalResponseBuilder.build_explanation_response(
                    question=question,
                    columns_meta=columns_meta,
                )

            return AIAskResponse(
                direct_answer=conv_res["direct_answer"],
                metrics=[],
                chart_data=None,
                table_data=None,
                interpretation=conv_res["direct_answer"],
                evidence=[],
                warnings=[],
                suggested_follow_ups=conv_res.get("suggested_follow_ups", []),
                plan=AnalyticalPlan(
                    intent="dataset_summary",
                    metric_column=col_names[0] if col_names else None,
                ),
                dataset_version_id=str(version.id),
                ai_status="operational",
            )

        # 2. Build minimal schema prompt metadata (Zero raw cell data by default)
        include_samples = getattr(settings, "AI_SEND_SAMPLE_VALUES", False)
        columns_summary = []
        for c in columns_meta:
            col_entry: dict[str, Any] = {
                "name": c["name"],
                "type": c.get("inferred_type", "string"),
            }
            if include_samples:
                col_entry["sample_values"] = c.get("sample_values", [])[:3]
            columns_summary.append(col_entry)

        # Build rich semantic context via AIContextBuilder
        semantic_summary = ""
        try:
            from app.services.intelligence.context_builder import AIContextBuilder
            sem_data = await AIContextBuilder.build_semantic_context(
                dataset=dataset, version=version, db=db, user_query=question
            )
            semantic_summary = sem_data.get("formatted_summary", "")
        except Exception as ex:
            logger.debug("Semantic context build omitted: %s", ex)

        schema_summary = {
            "dataset_name": dataset.name,
            "total_rows": version.row_count,
            "columns": columns_summary,
            "semantic_context": semantic_summary,
        }

        # 3. Plan Generation
        ai_status = "operational"
        try:
            raw_plan_dict, _ = await router.generate_analysis_plan(
                question=question,
                schema_metadata=schema_summary,
                conversation_history=formatted_history,
                dataset_sensitivity=getattr(dataset, "sensitivity_tier", "INTERNAL"),
            )
            plan = AnalyticalPlan(**raw_plan_dict)

        except DataLensException as err:
            if err.code == "AI_DISABLED":
                # Deterministic heuristic fallback when AI is disabled
                ai_status = "disabled"
                plan = cls._heuristic_plan_fallback(question, columns_meta)
            else:
                ai_status = "error"
                logger.warning(f"AI planner failed, falling back to heuristic plan: {err}")
                plan = cls._heuristic_plan_fallback(question, columns_meta)
        except Exception as err:
            ai_status = "error"
            logger.warning(f"AI planner error: {err}, using heuristic fallback")
            plan = cls._heuristic_plan_fallback(question, columns_meta)

        # 3. If clarification needed, return immediately
        if plan.needs_clarification:
            return AIAskResponse(
                direct_answer=plan.clarification_message or "Could you clarify which metric or dimension you would like to analyze?",
                interpretation="Awaiting user clarification before computing analytics.",
                plan=plan,
                ai_status=ai_status,
                suggested_follow_ups=[f"Analyze by {c['name']}" for c in columns_meta[:3]],
            )

        # 4. Strict Plan Validation
        validated_plan = PlanValidator.validate_and_normalize_plan(plan, columns_meta)

        # Convert plan filters to AnalyticsEngine FilterCondition models
        engine_filters = [
            FilterCondition(
                column=f.column,
                operator=f.operator,
                value=f.value,
                second_value=f.second_value,
            )
            for f in validated_plan.filters
        ]

        # 5. Deterministic Execution via DuckDB AnalyticsEngine
        run_type = validated_plan.intent
        metric_col = validated_plan.metric_column or (columns_meta[0]["name"])
        results_summary: dict[str, Any] = {}
        cards: list[AIMetricCard] = []
        chart: AIChartData | None = None
        table: AITableData | None = None
        direct_answer: str = ""
        evidence_items: list[AIEvidenceItem] = []
        warnings: list[str] = []


        if validated_plan.intent in ("group_by", "ranking", "filtered_aggregation"):
            group_cols = validated_plan.group_by_columns or [columns_meta[0]["name"]]
            agg_res = AnalyticsEngine.compute_aggregation(
                parquet_files=parquet_paths,
                group_by_columns=group_cols,
                metric_column=metric_col,
                aggregation=validated_plan.aggregation,
                sort_order=validated_plan.sort_direction,
                limit=validated_plan.limit,
                filters=engine_filters if engine_filters else None,
                version_id=str(version.id),
            )
            results_summary = agg_res.model_dump()

            top_item = agg_res.items[0] if agg_res.items else None
            if top_item:
                is_curr = any(k in metric_col.lower() for k in ("revenue", "sales", "price", "amount", "cost"))
                val_str = cls._format_currency_or_num(top_item.value, is_curr)
                tot_str = cls._format_currency_or_num(agg_res.total, is_curr)

                direct_answer = (
                    f"{top_item.key} generated the highest {metric_col} of {val_str}, "
                    f"accounting for {top_item.share_of_total or 0}% of the total ({tot_str})."
                )
                cards = [
                    AIMetricCard(label=f"Top {group_cols[0]}", value=top_item.key),
                    AIMetricCard(label=f"Top {metric_col}", value=val_str),
                    AIMetricCard(label="Share of Total", value=f"{top_item.share_of_total or 0}%"),
                    AIMetricCard(label="Total Aggregated", value=tot_str),
                ]

                # Visualizations
                chart = AIChartData(
                    type="bar",
                    title=f"{metric_col.title()} by {group_cols[0].title()}",
                    labels=[it.key for it in agg_res.items[:8]],
                    values=[it.value for it in agg_res.items[:8]],
                )
                table = AITableData(
                    headers=[group_cols[0].title(), metric_col.title(), "Transactions", "Share of Total"],
                    rows=[
                        [it.key, cls._format_currency_or_num(it.value, is_curr), it.count, f"{it.share_of_total or 0}%"]
                        for it in agg_res.items
                    ],
                )
            else:
                is_curr = any(k in metric_col.lower() for k in ("revenue", "sales", "price", "amount", "cost"))
                direct_answer = f"No records matched the analytical criteria for {metric_col} grouped by {group_cols[0]}."
                cards = [
                    AIMetricCard(label=f"Total {group_cols[0]}", value="0"),
                    AIMetricCard(label="Matching Records", value="0"),
                    AIMetricCard(label="Total Aggregated", value="$0.00" if is_curr else "0"),
                ]
                warnings.append("No records matched the filter criteria.")


            evidence_items.append(
                AIEvidenceItem(
                    id=f"ev-{uuid.uuid4().hex[:8]}",
                    title=f"{validated_plan.aggregation.upper()} Aggregation by {group_cols[0]}",
                    source_column=f"{group_cols[0]}, {metric_col}",
                    calculation_type=validated_plan.aggregation.capitalize(),
                    formula_or_query=f"{validated_plan.aggregation.upper()}({metric_col}) GROUP BY {group_cols[0]}",
                    raw_result=agg_res.total,
                    formatted_result=f"Total: {agg_res.total:,.2f}",
                    dataset_version_id=str(version.id),
                    row_count_analyzed=agg_res.row_count_analyzed,
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
            )

        elif validated_plan.intent == "time_series":
            ts_res = AnalyticsEngine.compute_time_series(
                parquet_files=parquet_paths,
                date_column=validated_plan.date_column or "date",
                value_column=metric_col,
                interval=validated_plan.time_granularity,
                aggregation=validated_plan.aggregation,
                filters=engine_filters if engine_filters else None,
                version_id=str(version.id),
            )
            results_summary = ts_res.model_dump()
            is_curr = any(k in metric_col.lower() for k in ("revenue", "sales", "price", "amount", "cost"))

            peak_pt = max(ts_res.points, key=lambda p: p.value) if ts_res.points else None
            if peak_pt:
                peak_str = cls._format_currency_or_num(peak_pt.value, is_curr)
                direct_answer = (
                    f"{metric_col.title()} peaked in {peak_pt.period} at {peak_str}. {ts_res.trend_summary}"
                )
                cards = [
                    AIMetricCard(label="Peak Period", value=peak_pt.period),
                    AIMetricCard(label="Peak Value", value=peak_str),
                    AIMetricCard(label="Total Aggregated", value=cls._format_currency_or_num(ts_res.total, is_curr)),
                ]
                chart = AIChartData(
                    type="line",
                    title=f"{metric_col.title()} Over Time ({validated_plan.time_granularity})",
                    labels=[pt.period for pt in ts_res.points],
                    values=[pt.value for pt in ts_res.points],
                )
                table = AITableData(
                    headers=["Period", metric_col.title(), "Growth Rate", "Transactions"],
                    rows=[
                        [
                            pt.period,
                            cls._format_currency_or_num(pt.value, is_curr),
                            f"{pt.growth_rate_pct:+.1f}%" if pt.growth_rate_pct is not None else "Baseline",
                            pt.count,
                        ]
                        for pt in ts_res.points
                    ],
                )
            else:
                direct_answer = f"No time series records found for {metric_col} over the selected time dimension."
                cards = [
                    AIMetricCard(label="Data Points", value="0"),
                    AIMetricCard(label="Total Aggregated", value="$0.00" if is_curr else "0"),
                ]
                warnings.append("No time series points found for the specified criteria.")


            evidence_items.append(
                AIEvidenceItem(
                    id=f"ev-{uuid.uuid4().hex[:8]}",
                    title="Temporal Aggregation",
                    source_column=f"{validated_plan.date_column}, {metric_col}",
                    calculation_type="Time Series",
                    formula_or_query=f"{validated_plan.aggregation.upper()}({metric_col}) GROUP BY {validated_plan.time_granularity}",
                    raw_result=ts_res.total,
                    formatted_result=f"Total: {ts_res.total:,.2f}",
                    dataset_version_id=str(version.id),
                    row_count_analyzed=ts_res.row_count_analyzed,
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
            )

        elif validated_plan.intent == "data_quality":
            qual_res = AnalyticsEngine.compute_data_quality(
                parquet_files=parquet_paths,
                columns_meta=columns_meta,
                version_id=str(version.id),
            )
            results_summary = qual_res.model_dump()
            direct_answer = f"Dataset Data Quality Score is {qual_res.quality_score}/100 with {len(qual_res.issues)} detected issues."
            cards = [
                AIMetricCard(label="Quality Score", value=f"{qual_res.quality_score} / 100"),
                AIMetricCard(label="Total Issues", value=str(len(qual_res.issues))),
                AIMetricCard(label="Total Rows", value=f"{qual_res.row_count_analyzed:,}"),
            ]
            table = AITableData(
                headers=["Issue Type", "Column", "Severity", "Affected Rows", "Suggested Action"],
                rows=[
                    [iss.type, iss.column or "Dataset", iss.severity.upper(), iss.affected_count, iss.suggested_action]
                    for iss in qual_res.issues
                ],
            )
            evidence_items.append(
                AIEvidenceItem(
                    id=f"ev-{uuid.uuid4().hex[:8]}",
                    title="Data Quality Audit",
                    source_column="*",
                    calculation_type="Quality Score",
                    formula_or_query="Tukey Outliers + Null Density + Duplicates Deduction",
                    raw_result=qual_res.quality_score,
                    formatted_result=f"Score: {qual_res.quality_score}",
                    dataset_version_id=str(version.id),
                    row_count_analyzed=qual_res.row_count_analyzed,
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
            )

        else:
            # Descriptive Stats / Dataset Summary
            desc_res = AnalyticsEngine.compute_descriptive_stats(
                parquet_files=parquet_paths,
                columns_meta=columns_meta,
                target_columns=[metric_col] if metric_col else None,
                filters=engine_filters if engine_filters else None,
                version_id=str(version.id),
            )
            results_summary = desc_res.model_dump()
            c_stat = desc_res.columns.get(metric_col)
            if c_stat:
                mean_str = f"{c_stat.mean:,.2f}" if c_stat.mean is not None else "N/A"
                median_str = f"{c_stat.median:,.2f}" if c_stat.median is not None else "N/A"
                min_str = f"{c_stat.min:,.2f}" if c_stat.min is not None else "N/A"
                max_str = f"{c_stat.max:,.2f}" if c_stat.max is not None else "N/A"
                direct_answer = (
                    f"Statistical profile for {metric_col}: Mean = {mean_str}, "
                    f"Median = {median_str}, Range = [{min_str} to {max_str}]."
                )
                cards = [
                    AIMetricCard(label="Mean", value=mean_str),
                    AIMetricCard(label="Median", value=median_str),
                    AIMetricCard(label="Std Deviation", value=f"{c_stat.standard_deviation:,.2f}" if c_stat.standard_deviation is not None else "N/A"),
                    AIMetricCard(label="IQR", value=f"{c_stat.iqr:,.2f}" if c_stat.iqr is not None else "N/A"),
                ]
            else:
                direct_answer = f"No statistical metrics available for {metric_col}."
                cards = [AIMetricCard(label="Status", value="No Data")]
                warnings.append("No descriptive statistics could be computed for the requested column.")


            evidence_items.append(
                AIEvidenceItem(
                    id=f"ev-{uuid.uuid4().hex[:8]}",
                    title="Descriptive Statistics",
                    source_column=metric_col,
                    calculation_type="Summary Stats",
                    formula_or_query=f"MEAN, MEDIAN, STDDEV({metric_col})",
                    raw_result=c_stat.mean if c_stat else 0,
                    formatted_result=f"Mean: {c_stat.mean if c_stat else 0}",
                    dataset_version_id=str(version.id),
                    row_count_analyzed=desc_res.row_count_analyzed,
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
            )

        execution_duration_ms = int((time.perf_counter() - start_time) * 1000)

        # 6. Persist to PostgreSQL AnalysisRun model
        analysis_run = AnalysisRun(
            dataset_id=dataset.id,
            dataset_version_id=version.id,
            analysis_type=run_type,
            parameters=validated_plan.model_dump(),
            result_summary=results_summary,
            status="completed",
            execution_time_ms=execution_duration_ms,
        )
        db.add(analysis_run)
        await db.commit()
        await db.refresh(analysis_run)

        # 7. AI Explanation Grounded in Verified Facts
        explanation = ""
        if ai_status == "operational":
            try:
                explanation, _ = await router.explain_results(
                    question=question,
                    plan=validated_plan.model_dump(),
                    results_summary=results_summary,
                    evidence={"dataset_version": version.version_number, "rows": version.row_count},
                    dataset_sensitivity=getattr(dataset, "sensitivity_tier", "INTERNAL"),
                )
            except Exception as e:
                logger.warning(f"AI explanation generation error: {e}")
                explanation = direct_answer
        else:
            explanation = direct_answer

        # 8. Follow-up Suggestions
        follow_ups = cls._generate_smart_follow_ups(validated_plan, columns_meta)

        return AIAskResponse(
            direct_answer=direct_answer,
            metrics=cards,
            chart_data=chart,
            table_data=table,
            interpretation=explanation or direct_answer,
            evidence=evidence_items,
            warnings=warnings,
            suggested_follow_ups=follow_ups,
            plan=validated_plan,
            analysis_run_id=str(analysis_run.id),
            dataset_version_id=str(version.id),
            ai_status=ai_status,
        )


    @classmethod
    def _heuristic_plan_fallback(
        cls,
        question: str,
        columns_meta: list[dict[str, Any]],
    ) -> AnalyticalPlan:
        """
        Deterministic intent parser used when AI is unconfigured, disabled, or unreachable.
        Guarantees users always receive working analytical answers from DuckDB.
        """
        q = question.lower()
        col_names = [c["name"] for c in columns_meta]
        num_cols = [c["name"] for c in columns_meta if c.get("inferred_type") in ("integer", "float", "number")]
        date_cols = [c["name"] for c in columns_meta if c.get("inferred_type") in ("date", "datetime") or "date" in c["name"].lower()]
        cat_cols = [c["name"] for c in columns_meta if c["name"] not in num_cols and c["name"] not in date_cols]

        metric = num_cols[0] if num_cols else col_names[0]
        group = cat_cols[0] if cat_cols else (col_names[1] if len(col_names) > 1 else col_names[0])

        if any(w in q for w in ("quality", "missing", "outlier", "duplicate", "clean")):
            return AnalyticalPlan(intent="data_quality")
        if any(w in q for w in ("trend", "monthly", "over time", "quarterly", "daily")):
            return AnalyticalPlan(
                intent="time_series",
                metric_column=metric,
                date_column=date_cols[0] if date_cols else None,
                time_granularity="monthly",
            )
        if any(w in q for w in ("top", "highest", "best", "ranking", "rank", "lead")):
            return AnalyticalPlan(
                intent="ranking",
                metric_column=metric,
                group_by_columns=[group],
                aggregation="sum",
                sort_direction="desc",
                limit=10,
            )
        if any(w in q for w in ("summary", "stats", "mean", "median", "average", "distribution")):
            return AnalyticalPlan(
                intent="descriptive_statistics",
                metric_column=metric,
            )

        return AnalyticalPlan(
            intent="group_by",
            metric_column=metric,
            group_by_columns=[group],
            aggregation="sum",
            sort_direction="desc",
            limit=10,
        )

    @classmethod
    def _generate_smart_follow_ups(
        cls,
        plan: AnalyticalPlan,
        columns_meta: list[dict[str, Any]],
    ) -> list[str]:
        suggestions: list[str] = []
        if plan.intent in ("group_by", "ranking"):
            suggestions.append("Show monthly trend over time")
            other_cats = [c["name"] for c in columns_meta if c["name"] not in plan.group_by_columns and c.get("inferred_type") == "string"]
            if other_cats:
                suggestions.append(f"Break down by {other_cats[0]}")
            suggestions.append("Audit data quality and outliers")
        elif plan.intent == "time_series":
            suggestions.append("Which category drove the peak month?")
            suggestions.append("Compare quarterly performance")
        else:
            suggestions.append("Which product generated highest revenue?")
            suggestions.append("Show monthly revenue trends")
        return suggestions[:3]

    @classmethod
    async def explain_analysis_run(
        cls,
        analysis_run: AnalysisRun,
        dataset: Dataset,
        audience: str = "Executive Board",
    ) -> str:
        router = AIProviderFactory.get_router()
        plan_dict = {
            "intent": analysis_run.run_type,
            "parameters": analysis_run.parameters or {},
        }
        results_summary = analysis_run.result_data or {}
        evidence = {
            "dataset_name": dataset.name,
            "analysis_id": str(analysis_run.id),
            "audience": audience,
        }
        question = f"Executive briefing for {audience} on {dataset.name} {analysis_run.run_type}"
        try:
            explanation, _ = await router.explain_results(
                question=question,
                plan=plan_dict,
                results_summary=results_summary,
                evidence=evidence,
                dataset_sensitivity=getattr(dataset, "sensitivity_tier", "INTERNAL"),
            )
            return explanation
        except Exception:
            return cls._fallback_explanation(
                AnalyticalPlan(intent="group_by"),
                results_summary,
                [],
            )

