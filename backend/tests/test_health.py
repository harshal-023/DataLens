import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "DataLens API"
    assert "/api/v1/health" in data["api_v1"]


@pytest.mark.asyncio
async def test_health_liveness_probe(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "ok",
        "service": "datalens-api",
    }


@pytest.mark.asyncio
async def test_health_readiness_probe_structure(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/ready")
    # Response code is either 200 (database running) or 503 (database offline)
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert data["service"] == "datalens-api"
    assert "components" in data
    assert "database" in data["components"]
    assert "timestamp" in data

    if response.status_code == 503:
        assert data["status"] == "unavailable"
        assert data["components"]["database"] == "disconnected"
        assert data["error"] is not None
    else:
        assert data["status"] == "ready"
        assert data["components"]["database"] == "connected"
        assert data["error"] is None


@pytest.mark.asyncio
async def test_cors_headers(async_client: AsyncClient):
    response = await async_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_structured_error_response_404(async_client: AsyncClient):
    response = await async_client.get("/api/v1/non_existent_route")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "HTTP_ERROR"
    assert data["error"]["message"] is not None

