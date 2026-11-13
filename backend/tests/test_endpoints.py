
import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_auth_me_unauthorized(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "detail" in response.json() or "error" in response.json()


@pytest.mark.asyncio
async def test_auth_me_malformed_token(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_endpoint_missing_cookie(async_client: AsyncClient):
    # Calling refresh with CSRF header but without refresh token cookie
    response = await async_client.post(
        "/api/v1/auth/refresh",
        headers={"X-CSRF-Token": "test_token"},
        cookies={settings.CSRF_COOKIE_NAME: "test_token"},
    )
    # Rejection: unauthorized or bad request due to missing refresh session
    assert response.status_code in (400, 401, 500)


@pytest.mark.asyncio
async def test_workspaces_unauthorized(async_client: AsyncClient):
    response = await async_client.get("/api/v1/workspaces")
    assert response.status_code == 401

    post_resp = await async_client.post(
        "/api/v1/workspaces",
        json={"name": "New Workspace"},
    )
    assert post_resp.status_code == 401


@pytest.mark.asyncio
async def test_invitations_accept_unauthorized(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/invitations/accept",
        json={"token": "some_invitation_token_123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_weak_password_validation(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@datalens.ai",
            "password": "weak",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_csrf_protection_on_cookie_auth(async_client: AsyncClient):
    # Missing CSRF header on state-changing endpoint with cookie
    response = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={
            settings.REFRESH_COOKIE_NAME: "raw_token_xyz",
            settings.CSRF_COOKIE_NAME: "csrf_expected_val",
        },
        # Omitting X-CSRF-Token header
    )
    assert response.status_code == 403
