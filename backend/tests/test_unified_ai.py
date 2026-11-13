"""Test suite for Phase 6A: Unified AI Architecture (Gemini + Local Ollama + Hybrid Routing)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies.auth import require_active_user
from app.main import app
from app.models.user import User
from app.services.ai.fallback_provider import DeterministicAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.hybrid_router import AITaskType, HybridAIRouter
from app.services.ai.ollama_provider import OllamaProvider


@pytest.fixture
def mock_user():
    return User(
        id=uuid.uuid4(),
        email="analyst@datalens.app",
        full_name="BI Analyst",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# 1. Deterministic Fallback Provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deterministic_provider_plan_and_explanation():
    """Verify deterministic fallback provider produces valid analytical plan and narrative without LLMs."""
    provider = DeterministicAIProvider()
    is_avail, _ = await provider.check_availability()
    assert is_avail is True

    schema = {"columns": ["revenue", "region", "customer_id"]}
    plan = await provider.generate_plan("Show total revenue by region", schema)
    assert plan["intent"] == "aggregation"
    assert plan["metric_column"] == "revenue"
    assert plan["aggregation"] == "sum"
    assert "region" in plan["group_by_columns"]

    explanation = await provider.generate_explanation(
        question="Show total revenue by region",
        plan=plan,
        results_summary={"total_rows": 100, "primary_value": "North America"},
        evidence={"dataset_version": "v1"},
    )
    assert "revenue" in explanation
    assert "DuckDB" in explanation


# ---------------------------------------------------------------------------
# 2. Ollama Local Provider (Mocked HTTPX)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ollama_provider_check_availability_offline():
    """Verify OllamaProvider gracefully catches connection errors when daemon is offline."""
    provider = OllamaProvider(base_url="http://localhost:99999", model="gemma3:4b", timeout_seconds=1)
    is_avail, err = await provider.check_availability()
    assert is_avail is False
    assert err is not None
    assert any(term in err.lower() for term in ("not reachable", "timed out", "failed", "connection"))


@pytest.mark.asyncio
async def test_ollama_provider_mocked_generation():
    """Verify OllamaProvider parses responses and tracks latency/tokens."""
    provider = OllamaProvider(base_url="http://localhost:11434", model="gemma3:4b")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": "Sales increased by 14% quarter-over-quarter.",
        "prompt_eval_count": 45,
        "eval_count": 22,
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await provider.generate_text("Analyze quarterly sales")
        assert res["text"] == "Sales increased by 14% quarter-over-quarter."
        assert res["input_tokens"] == 45
        assert res["output_tokens"] == 22
        assert res["provider"] == "ollama"


# ---------------------------------------------------------------------------
# 3. Hybrid AI Router: Task Routing & Privacy Enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_router_task_routing():
    """Verify task-based routing directs routine queries to Local AI and deep reasoning to Gemini."""
    mock_gemini = AsyncMock(spec=GeminiProvider)
    mock_gemini.check_availability.return_value = (True, None)

    mock_ollama = AsyncMock(spec=OllamaProvider)
    mock_ollama.check_availability.return_value = (True, None)

    router = HybridAIRouter(
        routing_mode="HYBRID",
        gemini_provider=mock_gemini,
        ollama_provider=mock_ollama,
    )

    # 1. Routine schema/SQL interpretation -> Local Ollama
    _, prov_name, reason = await router.select_provider(
        task_type=AITaskType.QUESTION_INTERPRETATION,
        dataset_sensitivity="INTERNAL",
        cloud_permitted_by_policy=True,
    )
    assert prov_name == "ollama"
    assert "local AI" in reason

    # 2. Executive report narratives -> Cloud Gemini
    _, prov_name2, reason2 = await router.select_provider(
        task_type=AITaskType.REPORT_NARRATIVE,
        dataset_sensitivity="INTERNAL",
        cloud_permitted_by_policy=True,
    )
    assert prov_name2 == "gemini"
    assert "Google Gemini" in reason2


@pytest.mark.asyncio
async def test_hybrid_router_privacy_enforcement_blocks_cloud():
    """Verify CONFIDENTIAL or RESTRICTED datasets strictly bar Gemini cloud routing."""
    mock_gemini = AsyncMock(spec=GeminiProvider)
    mock_gemini.check_availability.return_value = (True, None)

    mock_ollama = AsyncMock(spec=OllamaProvider)
    mock_ollama.check_availability.return_value = (True, None)

    router = HybridAIRouter(
        routing_mode="HYBRID",
        gemini_provider=mock_gemini,
        ollama_provider=mock_ollama,
    )

    # Even complex REPORT_NARRATIVE must NOT go to Gemini if dataset is RESTRICTED
    _, prov_name, reason = await router.select_provider(
        task_type=AITaskType.REPORT_NARRATIVE,
        dataset_sensitivity="RESTRICTED",
        cloud_permitted_by_policy=True,
    )
    assert prov_name == "ollama"
    assert "sensitivity policy requires local" in reason


@pytest.mark.asyncio
async def test_hybrid_router_fallback_when_local_offline():
    """Verify when preferred local AI is offline, router falls back to cloud (if permitted) or deterministic."""
    mock_gemini = AsyncMock(spec=GeminiProvider)
    mock_gemini.check_availability.return_value = (True, None)

    mock_ollama = AsyncMock(spec=OllamaProvider)
    mock_ollama.check_availability.return_value = (False, "Ollama offline")

    router = HybridAIRouter(
        routing_mode="HYBRID",
        gemini_provider=mock_gemini,
        ollama_provider=mock_ollama,
    )

    # Non-sensitive query: falls back to Gemini
    _, prov_name, reason = await router.select_provider(
        task_type=AITaskType.QUESTION_INTERPRETATION,
        dataset_sensitivity="INTERNAL",
        cloud_permitted_by_policy=True,
    )
    assert prov_name == "gemini"
    assert "Local AI offline" in reason

    # Sensitive query: cloud barred, must fall back to deterministic
    _, prov_name2, reason2 = await router.select_provider(
        task_type=AITaskType.QUESTION_INTERPRETATION,
        dataset_sensitivity="CONFIDENTIAL",
        cloud_permitted_by_policy=True,
    )
    assert prov_name2 == "deterministic"
    assert "barred by policy" in reason2


# ---------------------------------------------------------------------------
# 4. API Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_providers_list(mock_user):
    """Verify /api/v1/ai/providers returns providers status and active mode."""
    app.dependency_overrides[require_active_user] = lambda: mock_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/ai/providers")
        assert res.status_code == 200
        data = res.json()
        assert "active_routing_mode" in data
        assert "providers" in data
        names = [p["name"] for p in data["providers"]]
        assert "gemini" in names
        assert "ollama" in names
        assert "deterministic" in names
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_test_route_endpoint(mock_user):
    """Verify /api/v1/ai/route evaluates routing logic."""
    app.dependency_overrides[require_active_user] = lambda: mock_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/ai/route",
            json={
                "task_type": "QUESTION_INTERPRETATION",
                "dataset_sensitivity": "RESTRICTED",
                "cloud_permitted": True,
            },
        )
        assert res.status_code == 200
        data = res.json()
        # Must select ollama or deterministic, never gemini
        assert data["selected_provider"] in ("ollama", "deterministic")
        assert data["selected_provider"] != "gemini"
    app.dependency_overrides.clear()
