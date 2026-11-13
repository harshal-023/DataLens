import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.prompt_lab import PromptTemplate, PromptVersion
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.prompt_lab.analytics_service import PromptAnalyticsService
from app.services.prompt_lab.evaluator import PromptEvaluator
from app.services.prompt_lab.execution_service import PromptExecutionService
from app.services.prompt_lab.template_engine import PromptTemplateEngine
from tests.conftest import POSTGRES_AVAILABLE

# =========================================================================
# 1. TEMPLATE ENGINE & VARIABLE RENDERING TESTS
# =========================================================================

def test_template_engine_extract_variables():
    template = "Hello {{customer_name}}, your {{metric}} was {{value}} in {{region}}."
    vars_found = PromptTemplateEngine.extract_variables(template)
    assert vars_found == ["customer_name", "metric", "value", "region"]


def test_template_engine_extract_variables_empty():
    assert PromptTemplateEngine.extract_variables("") == []
    assert PromptTemplateEngine.extract_variables("No variables here.") == []


def test_template_engine_safe_render_success():
    sys_tpl = "You are an assistant for {{company}}."
    user_tpl = "Summarize sales in {{region}} for Q{{quarter}}."
    variables = {"company": "Acme Corp", "region": "EMEA", "quarter": 3}

    rendered_sys, rendered_user = PromptTemplateEngine.validate_and_render(
        sys_tpl, user_tpl, variables, required_variables=["company", "region"]
    )
    assert rendered_sys == "You are an assistant for Acme Corp."
    assert rendered_user == "Summarize sales in EMEA for Q3."


def test_template_engine_missing_required_variable():
    user_tpl = "Summarize sales in {{region}}."
    variables = {}

    with pytest.raises(Exception) as exc:
        PromptTemplateEngine.validate_and_render("", user_tpl, variables, required_variables=["region"])
    assert "MISSING_PROMPT_VARIABLES" in str(exc.value) or "Missing required" in str(exc.value)


def test_template_engine_unpopulated_variable():
    user_tpl = "Show me {{metric}} for {{dimension}}."
    variables = {"metric": "Revenue"}

    with pytest.raises(Exception) as exc:
        PromptTemplateEngine.validate_and_render("", user_tpl, variables)
    assert "UNPOPULATED_TEMPLATE_VARIABLES" in str(exc.value) or "Unpopulated" in str(exc.value)


# =========================================================================
# 2. EXECUTION SERVICE TESTS (SIMULATED & TOKEN / LATENCY ACCURACY)
# =========================================================================

@pytest.mark.asyncio
async def test_execution_service_simulated_mode():
    result = await PromptExecutionService.execute_prompt(
        system_prompt="You are a BI analyst for {{company}}.",
        user_prompt_template="Provide executive summary for {{product}}.",
        variables={"company": "DataLens", "product": "Analytics Hub"},
        provider="mock",
        model="gpt-4o-mini",
        temperature=0.5,
        max_tokens=500,
    )
    assert result["is_simulated"] is True
    assert result["provider_status"] == "simulated"
    assert "DataLens" in result["rendered_system_prompt"]
    assert "Analytics Hub" in result["rendered_user_prompt"]
    assert result["latency_ms"] > 0
    assert result["input_tokens"] > 0
    assert result["output_tokens"] > 0
    assert result["estimated_cost_usd"] is not None


@pytest.mark.asyncio
async def test_execution_service_json_format_simulation():
    result = await PromptExecutionService.execute_prompt(
        system_prompt="Return format as JSON object.",
        user_prompt_template="Analyze metrics for {{region}}.",
        variables={"region": "North America"},
        provider="mock",
    )
    assert result["is_simulated"] is True
    assert "{" in result["response_text"]
    assert "status" in result["response_text"]


# =========================================================================
# 3. EVALUATION ENGINE TESTS
# =========================================================================

def test_evaluator_exact_match():
    from app.schemas.prompt_lab import EvaluationCriterionConfig

    crit = [EvaluationCriterionConfig(metric_name="exact_match", max_score=1.0)]
    res_match = PromptEvaluator.evaluate_run("Target Answer", "Target Answer", [], crit)
    assert res_match[0]["score"] == 1.0

    res_no_match = PromptEvaluator.evaluate_run("Different Answer", "Target Answer", [], crit)
    assert res_no_match[0]["score"] == 0.0


def test_evaluator_keyword_presence():
    from app.schemas.prompt_lab import EvaluationCriterionConfig

    crit = [EvaluationCriterionConfig(metric_name="keyword_presence", max_score=1.0)]
    res = PromptEvaluator.evaluate_run(
        "Quarterly revenue grew by 14% with strong customer retention.",
        None,
        ["revenue", "retention", "profit"],
        crit,
    )
    # 2 out of 3 keywords present
    assert res[0]["score"] == pytest.approx(0.667, 0.01)
    assert res[0]["evaluation_method"] == "deterministic"


def test_evaluator_json_schema():
    from app.schemas.prompt_lab import EvaluationCriterionConfig

    crit = [EvaluationCriterionConfig(metric_name="json_schema_valid", max_score=1.0, parameters={"required_keys": ["status", "count"]})]
    res_valid = PromptEvaluator.evaluate_run('{"status": "ok", "count": 42}', None, [], crit)
    assert res_valid[0]["score"] == 1.0

    res_invalid = PromptEvaluator.evaluate_run('Not valid JSON', None, [], crit)
    assert res_invalid[0]["score"] == 0.0


def test_evaluator_response_length():
    from app.schemas.prompt_lab import EvaluationCriterionConfig

    crit = [EvaluationCriterionConfig(metric_name="response_length", max_score=1.0, parameters={"min_chars": 10, "max_chars": 50})]
    res_in_bounds = PromptEvaluator.evaluate_run("This text is exactly thirty chars.", None, [], crit)
    assert res_in_bounds[0]["score"] == 1.0

    res_too_short = PromptEvaluator.evaluate_run("Short", None, [], crit)
    assert res_too_short[0]["score"] < 1.0


def test_evaluator_model_assisted_metrics_labeling():
    from app.schemas.prompt_lab import EvaluationCriterionConfig

    crit = [
        EvaluationCriterionConfig(metric_name="relevance", max_score=1.0),
        EvaluationCriterionConfig(metric_name="instruction_following", max_score=1.0),
    ]
    res = PromptEvaluator.evaluate_run("A detailed, relevant response with bullet points: - Item 1", None, [], crit)
    for r in res:
        assert r["evaluation_method"] == "model_assisted"
        assert r["evaluated_by_model"] is not None
        assert "AI-Judged" in r["explanation"]


# =========================================================================
# 4. COMPARISON ANALYTICS TESTS
# =========================================================================

def test_prompt_analytics_comparison():
    class MockEval:
        def __init__(self, metric_name, score):
            self.metric_name = metric_name
            self.score = score

    class MockRun:
        def __init__(self, v_id, status, lat, inp_tok, out_tok, evals):
            self.prompt_version_id = uuid.UUID(v_id)
            self.status = status
            self.latency_ms = lat
            self.input_tokens = inp_tok
            self.output_tokens = out_tok
            self.estimated_cost_usd = 0.0001
            self.evaluation_results = evals

    v1_id = str(uuid.uuid4())
    v2_id = str(uuid.uuid4())

    runs = [
        MockRun(v1_id, "completed", 120, 50, 100, [MockEval("relevance", 0.8)]),
        MockRun(v1_id, "completed", 140, 50, 110, [MockEval("relevance", 0.85)]),
        MockRun(v2_id, "completed", 80, 45, 90, [MockEval("relevance", 0.95)]),
        MockRun(v2_id, "completed", 90, 45, 95, [MockEval("relevance", 0.98)]),
    ]

    version_numbers = {v1_id: 1, v2_id: 2}

    comparison = PromptAnalyticsService.compute_comparison(
        experiment_id=uuid.uuid4(),
        experiment_name="Prompt Benchmark",
        runs=runs,
        versions=version_numbers,
    )

    assert len(comparison.versions_compared) == 2
    # Version 2 should be recognized as best
    assert comparison.best_version_id == v2_id
    assert comparison.versions_compared[1].avg_latency_ms == 85.0
    assert comparison.versions_compared[1].avg_overall_score > comparison.versions_compared[0].avg_overall_score


# =========================================================================
# 5. LIVE POSTGRESQL & API INTEGRATION TESTS
# =========================================================================

@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="Live PostgreSQL not available")
@pytest.mark.asyncio
async def test_prompt_library_api_lifecycle():
    """
    Tests complete lifecycle: create template, list, get, update, duplicate, archive.
    """
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    TestSession = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with TestSession() as session:
            # Create user & workspace
            u = User(
                email=f"prompt_tester_{uuid.uuid4().hex[:6]}@example.com",
                password_hash=hash_password("Secr3tPassword!"),
                full_name="Prompt Tester",
                is_active=True,
            )
            session.add(u)
            await session.flush()

            ws = Workspace(
                name="Prompt Lab Workspace",
                owner_id=u.id,
            )
            session.add(ws)
            await session.flush()

            m = WorkspaceMembership(
                workspace_id=ws.id,
                user_id=u.id,
                role="owner",
            )
            session.add(m)
            await session.commit()

            user_id = u.id
            user_email = u.email
            ws_id = ws.id

        token = create_access_token(user_id, user_email)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": str(ws_id),
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create Prompt Template
            create_payload = {
                "name": "Customer KPI Summary",
                "description": "Generates KPI summaries for enterprise customers",
                "category": "Business Intelligence",
                "tags": ["kpi", "customers", "v1"],
                "system_prompt": "You are a senior data analyst for {{company}}.",
                "user_prompt_template": "Analyze metric {{metric}} for segment {{segment}}.",
                "variables": [
                    {"name": "company", "description": "Company name", "required": True},
                    {"name": "metric", "description": "KPI metric", "required": True},
                    {"name": "segment", "description": "Customer segment", "required": True},
                ],
                "model_config_snapshot": {
                    "provider": "mock",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
                "change_description": "Initial template creation",
            }

            resp = await client.post("/api/v1/prompts", json=create_payload, headers=headers)
            assert resp.status_code == 201, resp.text
            prompt_data = resp.json()
            assert prompt_data["name"] == "Customer KPI Summary"
            assert prompt_data["versions_count"] == 1
            assert prompt_data["current_version"]["version_number"] == 1
            prompt_id = prompt_data["id"]

            # 2. List Prompts
            resp_list = await client.get("/api/v1/prompts", headers=headers)
            assert resp_list.status_code == 200
            items = resp_list.json()
            assert any(item["id"] == prompt_id for item in items)

            # 3. Get Detail
            resp_get = await client.get(f"/api/v1/prompts/{prompt_id}", headers=headers)
            assert resp_get.status_code == 200
            assert resp_get.json()["id"] == prompt_id

            # 4. Update Metadata
            resp_patch = await client.patch(
                f"/api/v1/prompts/{prompt_id}",
                json={"name": "Updated KPI Summary", "category": "Data Analysis"},
                headers=headers,
            )
            assert resp_patch.status_code == 200
            assert resp_patch.json()["name"] == "Updated KPI Summary"
            assert resp_patch.json()["category"] == "Data Analysis"

            # 5. Create Version 2 (immutable versioning)
            v2_payload = {
                "system_prompt": "You are a principal analyst for {{company}}.",
                "user_prompt_template": "Provide executive breakdown of {{metric}} in {{segment}}.",
                "variables": [
                    {"name": "company", "required": True},
                    {"name": "metric", "required": True},
                    {"name": "segment", "required": True},
                ],
                "model_config_snapshot": {"provider": "mock", "model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 800},
                "change_description": "Version 2: Reduced temperature and enhanced executive tone",
            }
            resp_v2 = await client.post(f"/api/v1/prompts/{prompt_id}/versions", json=v2_payload, headers=headers)
            assert resp_v2.status_code == 201
            v2_data = resp_v2.json()
            assert v2_data["version_number"] == 2
            v2_id = v2_data["id"]

            # 6. List Versions
            resp_versions = await client.get(f"/api/v1/prompts/{prompt_id}/versions", headers=headers)
            assert resp_versions.status_code == 200
            v_list = resp_versions.json()
            assert len(v_list) == 2
            v1_id = v_list[1]["id"]

            # 7. Compare Versions (v1 vs v2)
            resp_cmp = await client.get(
                f"/api/v1/prompts/{prompt_id}/compare?version_a={v1_id}&version_b={v2_id}",
                headers=headers,
            )
            assert resp_cmp.status_code == 200
            cmp_data = resp_cmp.json()
            assert cmp_data["system_prompt_diff"] is True
            assert cmp_data["user_prompt_diff"] is True

            # 8. Restore Version 1 (creates Version 3 with v1 content, preserving history)
            resp_restore = await client.post(f"/api/v1/prompts/{prompt_id}/versions/{v1_id}/restore", headers=headers)
            assert resp_restore.status_code == 201
            v3_data = resp_restore.json()
            assert v3_data["version_number"] == 3
            assert "Restored from Version 1" in v3_data["change_description"]

            # 9. Duplicate Prompt
            resp_dup = await client.post(f"/api/v1/prompts/{prompt_id}/duplicate", headers=headers)
            assert resp_dup.status_code == 201
            dup_data = resp_dup.json()
            assert "(Copy)" in dup_data["name"]
            assert dup_data["id"] != prompt_id

            # 10. Archive Prompt
            resp_del = await client.delete(f"/api/v1/prompts/{prompt_id}", headers=headers)
            assert resp_del.status_code == 200
            # Archived prompt excluded by default
            resp_list_after = await client.get("/api/v1/prompts", headers=headers)
            assert not any(p["id"] == prompt_id for p in resp_list_after.json())

    finally:
        app.dependency_overrides.pop(get_db, None)
        await test_engine.dispose()


@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="Live PostgreSQL not available")
@pytest.mark.asyncio
async def test_experiment_lifecycle_and_evaluation_api():
    """
    Tests experiment creation, execution of test cases, evaluation scoring, and comparative analytics.
    """
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    TestSession = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with TestSession() as session:
            u = User(
                email=f"exp_tester_{uuid.uuid4().hex[:6]}@example.com",
                password_hash=hash_password("Secr3tPassword!"),
                full_name="Experiment Tester",
                is_active=True,
            )
            session.add(u)
            await session.flush()

            ws = Workspace(
                name="Experiment Workspace",
                owner_id=u.id,
            )
            session.add(ws)
            await session.flush()

            m = WorkspaceMembership(workspace_id=ws.id, user_id=u.id, role="owner")
            session.add(m)

            # Create Prompt Template with 2 Versions
            prompt = PromptTemplate(
                workspace_id=ws.id,
                name="Sentiment & KPI Classifier",
                category="Classification",
                tags=["sentiment"],
                created_by=u.id,
            )
            session.add(prompt)
            await session.flush()

            v1 = PromptVersion(
                prompt_id=prompt.id,
                version_number=1,
                system_prompt="You are a simple classifier.",
                user_prompt_template="Classify review: {{review_text}}",
                variables=[{"name": "review_text", "required": True}],
                model_config_snapshot={"provider": "mock", "model": "gpt-4o-mini"},
                change_description="Baseline v1",
            )
            v2 = PromptVersion(
                prompt_id=prompt.id,
                version_number=2,
                system_prompt="You are an expert enterprise feedback classifier. Format as JSON with category.",
                user_prompt_template="Classify review: {{review_text}}",
                variables=[{"name": "review_text", "required": True}],
                model_config_snapshot={"provider": "mock", "model": "gpt-4o-mini"},
                change_description="Structured v2",
            )
            session.add_all([v1, v2])
            await session.commit()

            user_id = u.id
            user_email = u.email
            ws_id = ws.id
            prompt_id = prompt.id
            v1_id = v1.id
            v2_id = v2.id

        token = create_access_token(user_id, user_email)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": str(ws_id),
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create Experiment with 2 Test Cases and 2 Versions
            exp_payload = {
                "name": "Classifier Benchmark",
                "description": "Comparing v1 baseline vs v2 structured classifier",
                "prompt_id": str(prompt_id),
                "version_ids": [str(v1_id), str(v2_id)],
                "test_cases": [
                    {
                        "name": "Positive Billing Review",
                        "variables": {"review_text": "Customer service was fantastic and billing was resolved quickly."},
                        "expected_output": None,
                        "expected_keywords": ["classification", "confidence"],
                    },
                    {
                        "name": "Negative Delivery Review",
                        "variables": {"review_text": "Product arrived three weeks late with damaged packaging."},
                        "expected_output": None,
                        "expected_keywords": ["classification"],
                    },
                ],
                "model_config_override": {"temperature": 0.2},
            }

            resp = await client.post("/api/v1/experiments", json=exp_payload, headers=headers)
            assert resp.status_code == 201, resp.text
            exp_data = resp.json()
            assert exp_data["name"] == "Classifier Benchmark"
            assert len(exp_data["test_cases"]) == 2
            exp_id = exp_data["id"]

            # 2. Run Experiment (2 versions × 2 test cases = 4 runs)
            resp_run = await client.post(f"/api/v1/experiments/{exp_id}/run", headers=headers)
            assert resp_run.status_code == 200
            run_data = resp_run.json()
            assert run_data["status"] == "completed"
            assert run_data["completed_runs_count"] == 4

            # 3. Get Results
            resp_results = await client.get(f"/api/v1/experiments/{exp_id}/results", headers=headers)
            assert resp_results.status_code == 200
            results = resp_results.json()
            assert len(results) == 4
            for r in results:
                assert r["status"] == "completed"
                assert r["latency_ms"] >= 0
                assert r["response_text"] is not None

            # 4. Evaluate Runs
            eval_payload = {
                "criteria": [
                    {"metric_name": "keyword_presence", "max_score": 1.0, "weight": 1.0},
                    {"metric_name": "relevance", "max_score": 1.0, "weight": 1.0},
                ]
            }
            resp_eval = await client.post(f"/api/v1/experiments/{exp_id}/evaluate", json=eval_payload, headers=headers)
            assert resp_eval.status_code == 200
            assert resp_eval.json()["evaluations_created"] == 8  # 4 runs * 2 criteria

            # 5. Get Comparison Dashboard Analytics
            resp_cmp = await client.get(f"/api/v1/experiments/{exp_id}/comparison", headers=headers)
            assert resp_cmp.status_code == 200
            cmp_res = resp_cmp.json()
            assert cmp_res["experiment_id"] == exp_id
            assert len(cmp_res["versions_compared"]) == 2
            assert cmp_res["best_version_id"] is not None

    finally:
        app.dependency_overrides.pop(get_db, None)
        await test_engine.dispose()
