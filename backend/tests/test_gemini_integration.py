import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.model_run import ModelRun
from app.models.user import User
from app.services.ai.factory import AIProviderFactory
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ml.insights import BusinessInsightEngine
from app.services.prompt_lab.evaluator import PromptEvaluator
from app.services.prompt_lab.execution_service import PromptExecutionService
from tests.conftest import POSTGRES_AVAILABLE

# =========================================================================
# 1. PROVIDER INITIALIZATION & FACTORY SELECTION
# =========================================================================

def test_gemini_provider_initialization():
    provider = GeminiProvider(api_key="AIzaSyTestValidKey123", model="gemini-2.5-flash", timeout_seconds=15)
    assert provider.model == "gemini-2.5-flash"
    assert provider.timeout_seconds == 15
    assert provider.api_key == "AIzaSyTestValidKey123"


def test_gemini_provider_missing_key_rejection():
    with pytest.raises(DataLensException) as exc:
        GeminiProvider(api_key="")
    assert exc.value.code == "AI_CONFIG_ERROR"


def test_ai_factory_selects_gemini():
    with (
        patch.object(settings, "AI_ENABLED", True),
        patch.object(settings, "AI_PROVIDER", "gemini"),
        patch.object(settings, "GEMINI_API_KEY", "AIzaSyTestKey"),
    ):
        provider = AIProviderFactory.get_provider()
        assert isinstance(provider, GeminiProvider)
        assert provider.model == settings.effective_ai_model


def test_ai_factory_unsupported_provider():
    with (
        patch.object(settings, "AI_ENABLED", True),
        patch.object(settings, "AI_PROVIDER", "unsupported_legacy_vendor"),
        patch.object(settings, "GEMINI_API_KEY", "AIzaSyTestKey"),
    ):
        with pytest.raises(DataLensException) as exc:
            AIProviderFactory.get_provider()
        assert exc.value.code == "UNSUPPORTED_AI_PROVIDER"


# =========================================================================
# 2. GEMINI AVAILABILITY & ERROR HANDLING
# =========================================================================

@pytest.mark.asyncio
async def test_gemini_availability_success():
    with patch("app.services.ai.gemini_provider.genai.Client") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.aio.models.get.return_value = AsyncMock()
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="AIzaSyMockKey")
        operational, error = await provider.check_availability()
        assert operational is True
        assert error is None


@pytest.mark.asyncio
async def test_gemini_availability_auth_failure():
    from google.genai import errors

    with patch("app.services.ai.gemini_provider.genai.Client") as mock_client_cls:
        mock_client = AsyncMock()
        err = errors.APIError(code=403, response_json={"error": "API_KEY_INVALID"})
        mock_client.aio.models.get.side_effect = err
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="AIzaSyInvalidKey")
        operational, error = await provider.check_availability()
        assert operational is False
        assert "authentication failed" in error.lower()


@pytest.mark.asyncio
async def test_gemini_availability_rate_limit():
    from google.genai import errors

    with patch("app.services.ai.gemini_provider.genai.Client") as mock_client_cls:
        mock_client = AsyncMock()
        err = errors.APIError(code=429, response_json={"error": "RESOURCE_EXHAUSTED"})
        mock_client.aio.models.get.side_effect = err
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="AIzaSyMockKey")
        operational, error = await provider.check_availability()
        assert operational is False
        assert "rate limit" in error.lower() or "quota" in error.lower()


@pytest.mark.asyncio
async def test_gemini_availability_timeout():
    with patch("app.services.ai.gemini_provider.genai.Client") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.aio.models.get.side_effect = TimeoutError("Timed out")
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="AIzaSyMockKey")
        operational, error = await provider.check_availability()
        assert operational is False
        assert "timed out" in error.lower()


# =========================================================================
# 3. PLAN GENERATION & EXPLANATION VIA GEMINI
# =========================================================================

@pytest.mark.asyncio
async def test_gemini_generate_plan_success():
    provider = GeminiProvider(api_key="AIzaSyMockKey")

    plan_json = {
        "intent": "group_by",
        "metric_column": "revenue",
        "group_by_columns": ["region"],
        "aggregation": "sum",
        "sort_direction": "desc",
        "limit": 5,
        "needs_clarification": False,
    }

    mock_resp = AsyncMock()
    mock_resp.text = json.dumps(plan_json)

    with patch.object(provider, "_execute_with_retry", return_value=mock_resp):
        plan = await provider.generate_plan(
            question="What is the total revenue by region?",
            schema_metadata={
                "dataset_name": "Sales Data",
                "columns": [
                    {"name": "region", "inferred_type": "string"},
                    {"name": "revenue", "inferred_type": "numeric"},
                ],
            },
        )
        assert plan["intent"] == "group_by"
        assert plan["metric_column"] == "revenue"
        assert plan["group_by_columns"] == ["region"]


@pytest.mark.asyncio
async def test_gemini_generate_plan_malformed_json():
    provider = GeminiProvider(api_key="AIzaSyMockKey")

    mock_resp = AsyncMock()
    mock_resp.text = "This is not valid JSON."

    with patch.object(provider, "_execute_with_retry", return_value=mock_resp):
        with pytest.raises(DataLensException) as exc:
            await provider.generate_plan(
                question="What is total sales?",
                schema_metadata={"columns": []},
            )
        assert exc.value.code == "AI_MALFORMED_PLAN"


@pytest.mark.asyncio
async def test_gemini_generate_explanation():
    provider = GeminiProvider(api_key="AIzaSyMockKey")

    expected_explanation = (
        "Total revenue across all regions reached $1,500,000, led by North America with $850,000."
    )
    mock_resp = AsyncMock()
    mock_resp.text = expected_explanation

    with patch.object(provider, "_execute_with_retry", return_value=mock_resp):
        explanation = await provider.generate_explanation(
            question="Revenue by region?",
            plan={"intent": "group_by", "metric_column": "revenue"},
            results_summary={"grand_total": 1500000, "top_performer": "North America"},
            evidence={"row_count": 4},
        )
        assert explanation == expected_explanation


# =========================================================================
# 4. TEXT GENERATION & STRUCTURED SYNTHESIS
# =========================================================================

@pytest.mark.asyncio
async def test_gemini_generate_text_and_tokens():
    provider = GeminiProvider(api_key="AIzaSyMockKey")

    mock_resp = AsyncMock()
    mock_resp.text = "Strategic recommendations: 1. Expand sales in EMEA."
    mock_resp.usage_metadata = AsyncMock(prompt_token_count=42, candidates_token_count=18)

    with patch.object(provider, "_execute_with_retry", return_value=mock_resp):
        res = await provider.generate_text("Suggest 1 recommendation")
        assert "EMEA" in res["text"]
        assert res["input_tokens"] == 42
        assert res["output_tokens"] == 18
        assert res["provider"] == "gemini"


@pytest.mark.asyncio
async def test_gemini_generate_structured():
    provider = GeminiProvider(api_key="AIzaSyMockKey")

    mock_resp = AsyncMock()
    mock_resp.text = json.dumps({"status": "approved", "risk_score": 0.12})

    with patch.object(provider, "_execute_with_retry", return_value=mock_resp):
        structured = await provider.generate_structured("Evaluate risk")
        assert structured["status"] == "approved"
        assert structured["risk_score"] == 0.12


# =========================================================================
# 5. BUSINESS INSIGHT ENGINE INTEGRATION
# =========================================================================

@pytest.mark.asyncio
async def test_business_insight_engine_with_gemini():
    dummy_run = ModelRun(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        model_type="anomaly_detection",
        algorithm="z_score",
        parameters={"target_column": "revenue"},
        feature_columns=["revenue"],
        metrics={"anomalies_detected_count": 2, "anomaly_percentage": 3.5},
        result_summary={"total_records_analyzed": 50},
        status="completed",
        duration_ms=45,
    )

    mock_insight_payload = {
        "insight_narrative": "Statistical audit confirmed two significant outliers in quarterly revenue.",
        "key_findings": ["Two data points diverged by more than 3 standard deviations.", "Baseline remains stable."],
        "limitations": ["Assumes normal distribution."],
        "suggested_actions": ["Verify invoice receipts for flagged periods."],
    }

    mock_provider = AsyncMock()
    mock_provider.generate_structured.return_value = mock_insight_payload

    with patch.object(AIProviderFactory, "get_provider", return_value=mock_provider):
        insight = await BusinessInsightEngine.generate_insight(dummy_run, audience="executive")
        assert insight.model_run_id == dummy_run.id
        assert "outliers in quarterly revenue" in insight.insight_narrative
        assert len(insight.key_findings) == 2
        assert insight.is_ai_generated is True


# =========================================================================
# 6. PROMPT LAB & EVALUATOR INTEGRATION
# =========================================================================

@pytest.mark.asyncio
async def test_prompt_execution_service_with_gemini():
    mock_provider = AsyncMock()
    mock_provider.generate_text.return_value = {
        "text": "Executive KPI Report: Revenue increased 15%.",
        "input_tokens": 50,
        "output_tokens": 25,
        "latency_ms": 110,
        "model": "gemini-2.5-flash",
        "provider": "gemini",
    }

    with (
        patch.object(settings, "AI_ENABLED", True),
        patch.object(settings, "GEMINI_API_KEY", "AIzaSyMockKey"),
        patch.object(AIProviderFactory, "get_provider", return_value=mock_provider),
    ):
        res = await PromptExecutionService.execute_prompt(
            system_prompt="You are a data advisor.",
            user_prompt_template="Summarize {{metric}}.",
            variables={"metric": "Revenue"},
            provider="gemini",
            model="gemini-2.5-flash",
        )
        assert res["provider"] == "gemini"
        assert res["is_simulated"] is False
        assert res["input_tokens"] == 50
        assert res["output_tokens"] == 25
        assert res["estimated_cost_usd"] is not None


@pytest.mark.asyncio
async def test_prompt_evaluator_with_gemini():
    mock_provider = AsyncMock()
    mock_provider.generate_structured.return_value = {
        "score": 0.95,
        "explanation": "Clear executive tone with thorough factual grounding.",
    }

    with (
        patch.object(settings, "AI_ENABLED", True),
        patch.object(settings, "GEMINI_API_KEY", "AIzaSyMockKey"),
        patch.object(AIProviderFactory, "get_provider", return_value=mock_provider),
    ):
        score, explanation = await PromptEvaluator.evaluate_with_gemini(
            metric="clarity",
            text="Revenue expanded 12% year-over-year in North America.",
        )
        assert score == 0.95
        assert "Clear executive tone" in explanation


# =========================================================================
# 7. LIVE DATABASE & ENDPOINT RBAC INTEGRATION
# =========================================================================

pytest_live = pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="Live PostgreSQL is offline on port 5432",
)


@pytest_live
@pytest.mark.asyncio
async def test_ai_status_endpoint_reports_gemini():
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with session_maker() as session:
            user = User(
                full_name="Gemini User",
                email=f"gemini_{uuid.uuid4().hex[:8]}@datalens.ai",
                password_hash=hash_password("ValidPass123!"),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            token = create_access_token(user.id, user.email)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(
                "/api/v1/ai/status",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["provider"] == "gemini"
            assert "gemini" in data["model"].lower()
            # Security verification: Never expose credentials in status response
            assert "api_key" not in data
            if settings.effective_ai_api_key:
                assert settings.effective_ai_api_key not in json.dumps(data)
    finally:
        app.dependency_overrides.pop(get_db, None)
        await test_engine.dispose()
