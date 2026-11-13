import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import (
    require_active_user,
    require_workspace_role,
)
from app.models.prompt_lab import (
    EvaluationResult,
    Experiment,
    ExperimentRun,
    PromptTemplate,
    PromptVersion,
    TestCase,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.prompt_lab import (
    EvaluateExperimentRequest,
    ExperimentComparisonResponse,
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentRunResponse,
    TestCaseResponse,
)
from app.services.prompt_lab.analytics_service import PromptAnalyticsService
from app.services.prompt_lab.evaluator import PromptEvaluator
from app.services.prompt_lab.execution_service import PromptExecutionService

router = APIRouter(prefix="/experiments", tags=["Prompt Lab - Experiments & Evaluation"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: ExperimentCreateRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentResponse:
    """
    Creates a new controlled prompt experiment with defined test cases and target prompt versions.
    """
    workspace, _ = ws_context

    # 1. Verify prompt versions exist and belong to the workspace if prompt_id is specified
    version_id_strs = [str(vid) for vid in payload.version_ids]
    if payload.prompt_id:
        p_stmt = select(PromptTemplate).where(PromptTemplate.id == payload.prompt_id, PromptTemplate.workspace_id == workspace.id)
        prompt = (await db.execute(p_stmt)).scalar_one_or_none()
        if not prompt:
            raise DataLensException("Prompt template not found in workspace.", code="NOT_FOUND")

    # Verify versions exist
    v_stmt = select(PromptVersion).where(PromptVersion.id.in_(payload.version_ids))
    found_versions = (await db.execute(v_stmt)).scalars().all()
    if len(found_versions) != len(payload.version_ids):
        raise DataLensException("One or more specified prompt versions were not found.", code="VERSION_NOT_FOUND")

    # 2. Create Experiment entity
    experiment = Experiment(
        workspace_id=workspace.id,
        prompt_id=payload.prompt_id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        version_ids=version_id_strs,
        model_config_override=payload.model_config_override,
        status="pending",
        created_by=current_user.id,
    )
    db.add(experiment)
    await db.flush()

    # 3. Create Test Cases
    created_tc_models = []
    for tc in payload.test_cases:
        tc_model = TestCase(
            experiment_id=experiment.id,
            name=tc.name.strip(),
            variables=tc.variables,
            expected_output=tc.expected_output,
            expected_keywords=tc.expected_keywords,
        )
        db.add(tc_model)
        created_tc_models.append(tc_model)

    await db.commit()
    await db.refresh(experiment)

    tc_responses = [
        TestCaseResponse(
            id=tc.id,
            experiment_id=tc.experiment_id,
            name=tc.name,
            variables=tc.variables,
            expected_output=tc.expected_output,
            expected_keywords=tc.expected_keywords,
            created_at=tc.created_at,
        )
        for tc in created_tc_models
    ]

    return ExperimentResponse(
        id=experiment.id,
        workspace_id=experiment.workspace_id,
        prompt_id=experiment.prompt_id,
        name=experiment.name,
        description=experiment.description,
        version_ids=experiment.version_ids,
        model_config_override=experiment.model_config_override,
        status=experiment.status,
        created_by=experiment.created_by,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        test_cases=tc_responses,
        runs_count=0,
        completed_runs_count=0,
    )


@router.get("", response_model=list[ExperimentResponse])
async def list_experiments(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    prompt_id: uuid.UUID | None = Query(None, description="Filter by prompt template ID"),
) -> list[ExperimentResponse]:
    """
    Lists experiments for the current workspace.
    """
    workspace, _ = ws_context
    stmt = (
        select(Experiment)
        .options(selectinload(Experiment.test_cases), selectinload(Experiment.runs))
        .where(Experiment.workspace_id == workspace.id)
    )
    if prompt_id:
        stmt = stmt.where(Experiment.prompt_id == prompt_id)

    stmt = stmt.order_by(desc(Experiment.created_at))
    result = await db.execute(stmt)
    experiments = result.scalars().all()

    items = []
    for exp in experiments:
        completed = sum(1 for r in exp.runs if r.status == "completed")
        tc_resps = [
            TestCaseResponse(
                id=tc.id,
                experiment_id=tc.experiment_id,
                name=tc.name,
                variables=tc.variables,
                expected_output=tc.expected_output,
                expected_keywords=tc.expected_keywords,
                created_at=tc.created_at,
            )
            for tc in exp.test_cases
        ]
        items.append(
            ExperimentResponse(
                id=exp.id,
                workspace_id=exp.workspace_id,
                prompt_id=exp.prompt_id,
                name=exp.name,
                description=exp.description,
                version_ids=exp.version_ids,
                model_config_override=exp.model_config_override,
                status=exp.status,
                created_by=exp.created_by,
                created_at=exp.created_at,
                updated_at=exp.updated_at,
                test_cases=tc_resps,
                runs_count=len(exp.runs),
                completed_runs_count=completed,
            )
        )
    return items


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment_detail(
    experiment_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentResponse:
    workspace, _ = ws_context
    stmt = (
        select(Experiment)
        .options(selectinload(Experiment.test_cases), selectinload(Experiment.runs))
        .where(Experiment.id == experiment_id, Experiment.workspace_id == workspace.id)
    )
    exp = (await db.execute(stmt)).scalar_one_or_none()
    if not exp:
        raise DataLensException("Experiment not found in workspace.", code="NOT_FOUND")

    completed = sum(1 for r in exp.runs if r.status == "completed")
    tc_resps = [
        TestCaseResponse(
            id=tc.id,
            experiment_id=tc.experiment_id,
            name=tc.name,
            variables=tc.variables,
            expected_output=tc.expected_output,
            expected_keywords=tc.expected_keywords,
            created_at=tc.created_at,
        )
        for tc in exp.test_cases
    ]

    return ExperimentResponse(
        id=exp.id,
        workspace_id=exp.workspace_id,
        prompt_id=exp.prompt_id,
        name=exp.name,
        description=exp.description,
        version_ids=exp.version_ids,
        model_config_override=exp.model_config_override,
        status=exp.status,
        created_by=exp.created_by,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        test_cases=tc_resps,
        runs_count=len(exp.runs),
        completed_runs_count=completed,
    )


@router.post("/{experiment_id}/run", response_model=ExperimentResponse)
async def run_experiment(
    experiment_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentResponse:
    """
    Executes all combinations of prompt versions and test cases in the experiment.
    Updates execution progress and records tokens, latency, and status.
    """
    workspace, _ = ws_context
    stmt = (
        select(Experiment)
        .options(selectinload(Experiment.test_cases), selectinload(Experiment.runs))
        .where(Experiment.id == experiment_id, Experiment.workspace_id == workspace.id)
    )
    exp = (await db.execute(stmt)).scalar_one_or_none()
    if not exp:
        raise DataLensException("Experiment not found in workspace.", code="NOT_FOUND")

    if exp.status == "running":
        raise DataLensException("Experiment is already currently running.", code="EXPERIMENT_ALREADY_RUNNING")

    # Load prompt versions
    v_uuids = [uuid.UUID(vid) for vid in exp.version_ids]
    v_stmt = select(PromptVersion).where(PromptVersion.id.in_(v_uuids))
    versions = (await db.execute(v_stmt)).scalars().all()
    version_map = {str(v.id): v for v in versions}

    exp.status = "running"
    await db.commit()

    # Track existing runs to avoid duplicate execution unless re-running
    existing_pairs = {(r.prompt_version_id, r.test_case_id) for r in exp.runs}

    has_failures = False
    for v_id_str in exp.version_ids:
        version = version_map.get(v_id_str)
        if not version:
            continue

        for tc in exp.test_cases:
            if (version.id, tc.id) in existing_pairs:
                continue

            # Model parameters
            cfg = dict(version.model_config_snapshot)
            if exp.model_config_override:
                cfg.update(exp.model_config_override)

            try:
                exec_result = await PromptExecutionService.execute_prompt(
                    system_prompt=version.system_prompt,
                    user_prompt_template=version.user_prompt_template,
                    variables=tc.variables,
                    provider=cfg.get("provider", "mock"),
                    model=cfg.get("model", "gpt-4o-mini"),
                    temperature=cfg.get("temperature", 0.7),
                    max_tokens=cfg.get("max_tokens", 1000),
                )

                run = ExperimentRun(
                    experiment_id=exp.id,
                    prompt_version_id=version.id,
                    test_case_id=tc.id,
                    rendered_system_prompt=exec_result["rendered_system_prompt"],
                    rendered_user_prompt=exec_result["rendered_user_prompt"],
                    response_text=exec_result["response_text"],
                    provider=exec_result["provider"],
                    model=exec_result["model"],
                    status="completed",
                    input_tokens=exec_result["input_tokens"],
                    output_tokens=exec_result["output_tokens"],
                    latency_ms=exec_result["latency_ms"],
                    estimated_cost_usd=exec_result["estimated_cost_usd"],
                )
                db.add(run)
            except Exception as e:
                has_failures = True
                run = ExperimentRun(
                    experiment_id=exp.id,
                    prompt_version_id=version.id,
                    test_case_id=tc.id,
                    rendered_system_prompt="",
                    rendered_user_prompt="",
                    response_text=None,
                    provider=cfg.get("provider", "mock"),
                    model=cfg.get("model", "gpt-4o-mini"),
                    status="failed",
                    error_message=str(e),
                )
                db.add(run)

    exp.status = "failed" if (has_failures and not exp.runs) else "completed"
    await db.commit()
    await db.refresh(exp)

    # Re-fetch with loaded relationships
    refetch = (
        select(Experiment)
        .options(selectinload(Experiment.test_cases), selectinload(Experiment.runs))
        .where(Experiment.id == exp.id)
    )
    exp = (await db.execute(refetch)).scalar_one()

    completed = sum(1 for r in exp.runs if r.status == "completed")
    tc_resps = [
        TestCaseResponse(
            id=tc.id,
            experiment_id=tc.experiment_id,
            name=tc.name,
            variables=tc.variables,
            expected_output=tc.expected_output,
            expected_keywords=tc.expected_keywords,
            created_at=tc.created_at,
        )
        for tc in exp.test_cases
    ]

    return ExperimentResponse(
        id=exp.id,
        workspace_id=exp.workspace_id,
        prompt_id=exp.prompt_id,
        name=exp.name,
        description=exp.description,
        version_ids=exp.version_ids,
        model_config_override=exp.model_config_override,
        status=exp.status,
        created_by=exp.created_by,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        test_cases=tc_resps,
        runs_count=len(exp.runs),
        completed_runs_count=completed,
    )


@router.post("/{experiment_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_experiment(
    experiment_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Cancels an experiment without corrupting completed partial runs.
    """
    workspace, _ = ws_context
    stmt = select(Experiment).where(Experiment.id == experiment_id, Experiment.workspace_id == workspace.id)
    exp = (await db.execute(stmt)).scalar_one_or_none()
    if not exp:
        raise DataLensException("Experiment not found in workspace.", code="NOT_FOUND")

    if exp.status in ("completed", "failed"):
        raise DataLensException(f"Cannot cancel experiment in '{exp.status}' state.", code="INVALID_STATE")

    exp.status = "cancelled"
    await db.commit()
    return {"message": f"Experiment '{exp.name}' has been cancelled.", "status": "cancelled"}


@router.get("/{experiment_id}/results", response_model=list[ExperimentRunResponse])
async def get_experiment_results(
    experiment_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ExperimentRunResponse]:
    """
    Lists execution runs with generated outputs, token usage, latency, and attached evaluation scores.
    """
    workspace, _ = ws_context
    stmt = (
        select(Experiment)
        .where(Experiment.id == experiment_id, Experiment.workspace_id == workspace.id)
    )
    exp = (await db.execute(stmt)).scalar_one_or_none()
    if not exp:
        raise DataLensException("Experiment not found in workspace.", code="NOT_FOUND")

    r_stmt = (
        select(ExperimentRun)
        .options(selectinload(ExperimentRun.evaluation_results))
        .where(ExperimentRun.experiment_id == experiment_id)
        .order_by(ExperimentRun.created_at.asc())
    )
    runs = (await db.execute(r_stmt)).scalars().all()

    items = []
    for r in runs:
        eval_list = [
            {
                "id": str(ev.id),
                "metric_name": ev.metric_name,
                "score": ev.score,
                "max_score": ev.max_score,
                "evaluation_method": ev.evaluation_method,
                "explanation": ev.explanation,
                "evaluated_by_model": ev.evaluated_by_model,
            }
            for ev in r.evaluation_results
        ]
        items.append(
            ExperimentRunResponse(
                id=r.id,
                experiment_id=r.experiment_id,
                prompt_version_id=r.prompt_version_id,
                test_case_id=r.test_case_id,
                rendered_system_prompt=r.rendered_system_prompt,
                rendered_user_prompt=r.rendered_user_prompt,
                response_text=r.response_text,
                provider=r.provider,
                model=r.model,
                status=r.status,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                latency_ms=r.latency_ms,
                estimated_cost_usd=r.estimated_cost_usd,
                error_message=r.error_message,
                created_at=r.created_at,
                evaluations=eval_list,
            )
        )
    return items


@router.post("/{experiment_id}/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_experiment(
    experiment_id: uuid.UUID,
    payload: EvaluateExperimentRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Evaluates completed experiment runs against configured deterministic and model-assisted metrics.
    """
    workspace, _ = ws_context
    stmt = (
        select(Experiment)
        .options(selectinload(Experiment.runs), selectinload(Experiment.test_cases))
        .where(Experiment.id == experiment_id, Experiment.workspace_id == workspace.id)
    )
    exp = (await db.execute(stmt)).scalar_one_or_none()
    if not exp:
        raise DataLensException("Experiment not found in workspace.", code="NOT_FOUND")

    tc_map = {tc.id: tc for tc in exp.test_cases}

    eval_count = 0
    for run in exp.runs:
        if run.status != "completed":
            continue

        tc = tc_map.get(run.test_case_id)
        exp_out = tc.expected_output if tc else None
        exp_kw = tc.expected_keywords if tc else []
        tc_vars = tc.variables if tc else {}

        eval_records = PromptEvaluator.evaluate_run(
            response_text=run.response_text,
            expected_output=exp_out,
            expected_keywords=exp_kw,
            criteria=payload.criteria,
            run_status=run.status,
            variables=tc_vars,
        )

        for er in eval_records:
            eval_model = EvaluationResult(
                run_id=run.id,
                metric_name=er["metric_name"],
                score=er["score"],
                max_score=er["max_score"],
                evaluation_method=er["evaluation_method"],
                explanation=er["explanation"],
                evaluated_by_model=er["evaluated_by_model"],
            )
            db.add(eval_model)
            eval_count += 1

    await db.commit()
    return {
        "message": f"Successfully computed {eval_count} evaluation scores across {len(exp.runs)} runs.",
        "evaluations_created": eval_count,
    }


@router.get("/{experiment_id}/comparison", response_model=ExperimentComparisonResponse)
async def get_experiment_comparison(
    experiment_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentComparisonResponse:
    """
    Returns aggregated comparative analytics across versions in the experiment.
    """
    workspace, _ = ws_context
    stmt = (
        select(Experiment)
        .options(selectinload(Experiment.runs).selectinload(ExperimentRun.evaluation_results))
        .where(Experiment.id == experiment_id, Experiment.workspace_id == workspace.id)
    )
    exp = (await db.execute(stmt)).scalar_one_or_none()
    if not exp:
        raise DataLensException("Experiment not found in workspace.", code="NOT_FOUND")

    # Fetch prompt versions to get version numbers
    v_uuids = [uuid.UUID(vid) for vid in exp.version_ids]
    v_stmt = select(PromptVersion).where(PromptVersion.id.in_(v_uuids))
    versions = (await db.execute(v_stmt)).scalars().all()
    version_numbers = {str(v.id): v.version_number for v in versions}

    return PromptAnalyticsService.compute_comparison(
        experiment_id=exp.id,
        experiment_name=exp.name,
        runs=exp.runs,
        versions=version_numbers,
    )

