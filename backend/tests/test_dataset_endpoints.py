import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_dataset_list_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/datasets")
        assert res.status_code == 401
        body = res.json()
        assert "detail" in body or "error" in body


@pytest.mark.asyncio
async def test_dataset_upload_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/datasets",
            data={"name": "Test Dataset"},
            files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_dataset_detail_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        random_id = uuid.uuid4()
        res = await client.get(f"/api/v1/datasets/{random_id}")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_dataset_rows_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        random_id = uuid.uuid4()
        res = await client.get(f"/api/v1/datasets/{random_id}/rows")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_dataset_download_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        random_id = uuid.uuid4()
        v_id = uuid.uuid4()
        res = await client.get(f"/api/v1/datasets/{random_id}/versions/{v_id}/download")
        assert res.status_code == 401
