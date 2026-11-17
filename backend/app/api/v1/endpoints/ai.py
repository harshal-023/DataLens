import json
import time
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import (
    require_active_user,
    require_workspace_role,
)
from app.models.analysis_run import AnalysisRun
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.user import User
from app.models.workspace import Workspace
from app.services.ai.factory import AIProviderFactory
from app.services.ai.intent_classifier import ConversationalResponseBuilder, IntentClassifier
from app.services.ai.orchestrator import AIAnalyticsOrchestrator
from app.services.ai.schemas import (
    AIAskRequest,
    AIAskResponse,
    AIChatRequest,
    AIChatResponse,
    AIClarifyRequest,
    AIExplainRequest,
    AIExplainResponse,
    AIOllamaModelsResponse,
    AIPrivacyPolicyCreate,
    AIPrivacyPolicyResponse,
    AIProviderInfo,
    AIProvidersListResponse,
    AIRouteDecisionResponse,
    AIRouteRequest,
    AIStatusResponse,
)
from app.services.ai.validator import PlanValidator

router = APIRouter(prefix="/ai", tags=["AI Analytics"])


async def _resolve_dataset_and_parts(
    dataset_id: uuid.UUID,
    workspace_id: uuid.UUID,
    version_id: uuid.UUID | None,
    db: AsyncSession,
) -> tuple[Dataset, DatasetVersion, list[Path], list[dict[str, Any]]]:
    stmt = (
        select(Dataset)
        .options(
            selectinload(Dataset.versions),
            selectinload(Dataset.current_version),
        )
        .where(
            Dataset.id == dataset_id,
            Dataset.workspace_id == workspace_id,
            Dataset.is_archived.is_(False),
        )
    )
    res = await db.execute(stmt)
    dataset = res.scalar_one_or_none()
    if not dataset:
        raise DataLensException("Dataset not found in this workspace.", code="NOT_FOUND")

    target_ver_id = version_id or dataset.current_version_id
    if not target_ver_id:
        raise DataLensException("Dataset has no active version to analyze.", code="NOT_FOUND")

    ver_stmt = select(DatasetVersion).where(
        DatasetVersion.id == target_ver_id,
        DatasetVersion.dataset_id == dataset.id,
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
    columns_meta = manifest.get("columns", [])

    return dataset, version, parquet_paths, columns_meta


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status(
    current_user: Annotated[User, Depends(require_active_user)],
) -> AIStatusResponse:
    """
    Checks AI provider connectivity and status without leaking API credentials.
    """
    if not settings.AI_ENABLED:
        return AIStatusResponse(
            ai_enabled=False,
            provider=settings.AI_PROVIDER,
            model=settings.effective_ai_model,
            operational=False,
            error="AI analytics is currently disabled in system settings.",
        )

    provider = AIProviderFactory.get_provider()
    operational, error_msg = await provider.check_availability()
    return AIStatusResponse(
        ai_enabled=True,
        provider=settings.AI_PROVIDER,
        model=settings.effective_ai_model,
        operational=operational,
        error=error_msg,
    )


@router.post("/ask", response_model=AIAskResponse)
async def ask_question(
    req: AIAskRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIAskResponse:
    """
    Parses a natural-language business question into an analytical plan,
    validates it against dataset schema, deterministically computes via DuckDB,
    and returns verified evidence and grounded executive explanation.
    """
    workspace, _ = ws_context
    dataset, version, parquet_paths, columns_meta = await _resolve_dataset_and_parts(
        req.dataset_id, workspace.id, req.version_id, db
    )

    return await AIAnalyticsOrchestrator.process_question(
        question=req.question,
        dataset=dataset,
        version=version,
        parquet_paths=parquet_paths,
        columns_meta=columns_meta,
        user_id=current_user.id,
        db=db,
        conversation_history=req.conversation_history,
    )


@router.post("/clarify", response_model=AIAskResponse)
async def clarify_question(
    req: AIClarifyRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIAskResponse:
    """
    Refines an analytical question using user-supplied clarification.
    """
    workspace, _ = ws_context
    dataset, version, parquet_paths, columns_meta = await _resolve_dataset_and_parts(
        req.dataset_id, workspace.id, req.version_id, db
    )

    # Validate that the original plan itself conforms to the real schema
    PlanValidator.validate_and_normalize_plan(req.original_plan, columns_meta)

    combined_question = f"{req.question} (Clarification: {req.user_clarification})"

    history = [
        {"role": "user", "content": req.question},
        {
            "role": "assistant",
            "content": f"Understood plan intent: {req.original_plan.intent} on column {req.original_plan.metric_column}. Please clarify parameters.",
        },
        {"role": "user", "content": req.user_clarification},
    ]

    return await AIAnalyticsOrchestrator.process_question(
        question=combined_question,
        dataset=dataset,
        version=version,
        parquet_paths=parquet_paths,
        columns_meta=columns_meta,
        user_id=current_user.id,
        db=db,
        conversation_history=history,
    )


@router.post("/explain", response_model=AIExplainResponse)
async def explain_analysis(
    req: AIExplainRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIExplainResponse:
    """
    Generates a fresh grounded executive explanation for an existing analysis run.
    """
    workspace, _ = ws_context
    stmt = select(Dataset).where(
        Dataset.id == req.dataset_id,
        Dataset.workspace_id == workspace.id,
        Dataset.is_archived.is_(False),
    )
    dataset = (await db.execute(stmt)).scalar_one_or_none()
    if not dataset:
        raise DataLensException("Dataset not found in this workspace.", code="NOT_FOUND")

    run_stmt = select(AnalysisRun).where(
        AnalysisRun.id == req.analysis_run_id,
        AnalysisRun.dataset_id == dataset.id,
    )
    analysis_run = (await db.execute(run_stmt)).scalar_one_or_none()
    if not analysis_run:
        raise DataLensException("Analysis run not found for this dataset.", code="NOT_FOUND")

    explanation = await AIAnalyticsOrchestrator.explain_analysis_run(
        analysis_run=analysis_run,
        dataset=dataset,
        audience=req.audience,
    )

    return AIExplainResponse(
        analysis_run_id=str(analysis_run.id),
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# Conversational AI Chat Endpoint (Google Gemini Mobile-App Experience)
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_ai(
    req: AIChatRequest,
    current_user: Annotated[User, Depends(require_active_user)],
) -> AIChatResponse:
    """
    Direct conversational AI chatbot endpoint powered by Google Gemini.
    Delivers fluid, articulate, conversational BI assistance matching ChatGPT and the Gemini mobile app.
    Works seamlessly with or without an active backend dataset.
    """
    start_time = time.perf_counter()

    col_names = []
    if req.columns:
        col_names = [c["name"] if isinstance(c, dict) and "name" in c else str(c) for c in req.columns]

    formatted_history = None
    if req.conversation_history:
        formatted_history = [
            {"role": m.role, "content": m.content}
            for m in req.conversation_history
        ]

    # Classify incoming message intent
    intent = IntentClassifier.classify(
        question=req.message,
        conversation_history=formatted_history,
        columns=col_names,
    )

    suggested_qs = [
        "Which product generated the highest revenue?",
        "Show monthly revenue trend",
        "Compare regional performance",
        "What are the top key metrics?",
    ]

    conv_res = await ConversationalResponseBuilder.build_conversational_response_async(
        question=req.message,
        intent=intent,
        dataset_name=req.dataset_name,
        row_count=req.row_count,
        columns=req.columns,
        conversation_history=formatted_history,
        suggested_questions=suggested_qs,
    )

    latency_ms = conv_res.get("latency_ms") or int((time.perf_counter() - start_time) * 1000)

    return AIChatResponse(
        direct_answer=conv_res["direct_answer"],
        content=conv_res["content"],
        intent=conv_res["intent"],
        suggested_follow_ups=conv_res.get("suggested_follow_ups", suggested_qs[:3]),
        latency_ms=latency_ms,
        provider=conv_res.get("provider", "gemini"),
        model=conv_res.get("model", ""),
    )



# ---------------------------------------------------------------------------
# Phase 6A: Unified Provider Architecture & Privacy Endpoints
# ---------------------------------------------------------------------------


@router.get("/providers", response_model=AIProvidersListResponse)
async def list_ai_providers(
    current_user: Annotated[User, Depends(require_active_user)],
) -> AIProvidersListResponse:
    """Lists operational status, active models, and configurations for all AI providers."""
    router_inst = AIProviderFactory.get_router()
    health = await router_inst.health_check_all()

    providers_info: list[AIProviderInfo] = []
    for name, p_data in health["providers"].items():
        providers_info.append(
            AIProviderInfo(
                name=name,
                configured=p_data.get("configured", False),
                operational=p_data.get("operational", False),
                model=p_data.get("model", ""),
                base_url=p_data.get("base_url"),
                execution_mode="local_inference" if name == "ollama" else ("cloud_inference" if name == "gemini" else "offline_rules"),
                error=p_data.get("error"),
            )
        )

    return AIProvidersListResponse(
        active_routing_mode=health["active_routing_mode"],
        providers=providers_info,
        recommended_local_model="gemma3:4b",
    )


@router.get("/ollama/models", response_model=AIOllamaModelsResponse)
async def get_ollama_models(
    current_user: Annotated[User, Depends(require_active_user)],
) -> AIOllamaModelsResponse:
    """Discovers installed Ollama models from local Ollama daemon."""
    ollama_prov = AIProviderFactory.get_ollama_provider()
    model_info = await ollama_prov.get_model_information()
    return AIOllamaModelsResponse(
        is_online=model_info.get("is_online", False),
        base_url=ollama_prov.base_url,
        models=model_info.get("installed_models", []),
    )


@router.post("/route", response_model=AIRouteDecisionResponse)
async def test_ai_route(
    req: AIRouteRequest,
    current_user: Annotated[User, Depends(require_active_user)],
) -> AIRouteDecisionResponse:
    """Simulates provider routing decision for a given task and dataset privacy level."""
    router_inst = AIProviderFactory.get_router()
    _, provider_name, reason = await router_inst.select_provider(
        task_type=req.task_type,
        dataset_sensitivity=req.dataset_sensitivity,
        cloud_permitted_by_policy=req.cloud_permitted,
    )
    return AIRouteDecisionResponse(
        selected_provider=provider_name,
        reason=reason,
        routing_mode=router_inst.routing_mode,
        cloud_permitted=req.cloud_permitted,
        dataset_sensitivity=req.dataset_sensitivity,
    )


@router.get("/privacy-policy", response_model=AIPrivacyPolicyResponse)
async def get_workspace_ai_privacy_policy(
    workspace_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_active_user)],
) -> AIPrivacyPolicyResponse:
    """Fetch workspace AI privacy policy and routing constraints."""
    from app.models.ai import AIPrivacyPolicy

    stmt = select(AIPrivacyPolicy).where(AIPrivacyPolicy.workspace_id == workspace_id)
    policy = (await db.execute(stmt)).scalar_one_or_none()
    if not policy:
        # Create default policy
        policy = AIPrivacyPolicy(
            workspace_id=workspace_id,
            routing_mode="HYBRID",
            cloud_ai_permitted=True,
            local_only_enforced=False,
            allow_sample_values=False,
            min_sensitivity_for_local_only="CONFIDENTIAL",
            default_local_model="gemma3:4b",
            default_cloud_model="gemini-3.5-flash",
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)

    return AIPrivacyPolicyResponse.model_validate(policy)


@router.put("/privacy-policy", response_model=AIPrivacyPolicyResponse)
async def update_workspace_ai_privacy_policy(
    workspace_id: uuid.UUID,
    policy_in: AIPrivacyPolicyCreate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_active_user)],
) -> AIPrivacyPolicyResponse:
    """Update workspace AI privacy policy and routing constraints."""
    from app.models.ai import AIPrivacyPolicy

    stmt = select(AIPrivacyPolicy).where(AIPrivacyPolicy.workspace_id == workspace_id)
    policy = (await db.execute(stmt)).scalar_one_or_none()
    if not policy:
        policy = AIPrivacyPolicy(workspace_id=workspace_id)
        db.add(policy)

    update_data = policy_in.model_dump()
    for field, val in update_data.items():
        setattr(policy, field, val)

    await db.commit()
    await db.refresh(policy)
    return AIPrivacyPolicyResponse.model_validate(policy)
