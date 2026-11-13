"""Tests for External Data Source Connections Endpoints & Import Engine."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.connectors.base import BaseConnector
from app.connectors.registry import ConnectorRegistry
from app.core.config import settings
from app.dependencies.auth import require_active_user
from app.main import app
from app.models.data_source import DataSourceConnection
from app.models.user import User
from app.services.connectors.import_engine import ImportEngine


@pytest.fixture(autouse=True)
def override_auth():
    mock_user = User(
        id=uuid.uuid4(),
        email="test_admin@datalens.app",
        full_name="Test Admin",
        is_active=True,
    )
    app.dependency_overrides[require_active_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(require_active_user, None)


@pytest.mark.asyncio
async def test_list_connectors_endpoint():
    """Verify metadata endpoint returns 6 supported connector definitions."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/v1/connections/connectors")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 6
        types = {c["type"] for c in data}
        assert {"postgres", "mysql", "rest_api", "google_sheets", "mongodb", "s3"}.issubset(types)


@pytest.mark.asyncio
async def test_google_auth_url_endpoint():
    """Verify Google OAuth auth-url generation endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/v1/connections/oauth/google/auth-url?client_id=my-client-id&redirect_uri=https://datalens.app/callback",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "accounts.google.com" in data["auth_url"]
        assert "my-client-id" in data["auth_url"]
        assert "state" in data


@pytest.mark.asyncio
async def test_on_the_fly_test_endpoint():
    """Verify POST /api/v1/connections/test endpoint."""
    mock_connector = MagicMock(spec=BaseConnector)
    mock_connector.test_connection = AsyncMock(return_value={
        "status": "success",
        "latency_ms": 14.2,
        "message": "Connection OK",
        "server_version": "16.1",
    })
    mock_connector.close = AsyncMock()

    with patch.object(ConnectorRegistry, "get", return_value=mock_connector):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/connections/test",
                json={
                    "source_type": "postgres",
                    "config": {"host": "localhost", "port": 5432, "database": "db"},
                    "credentials": {"username": "user", "password": "pass"},
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["latency_ms"] == 14.2
            assert data["message"] == "Connection OK"


@pytest.mark.asyncio
async def test_import_engine_parquet_materialization(tmp_path, monkeypatch):
    """Test ImportEngine streaming, chunking into Parquet, writing manifest, and generating immutable dataset version."""
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))

    class MockStreamingConnector(BaseConnector):
        async def test_connection(self):
            return {"status": "success"}

        async def discover(self):
            return {"schemas": {}}

        async def get_schema(self, resource_path):
            return []

        async def preview(self, resource_path, limit=100):
            return {}

        async def stream_data(self, resource_path, chunk_size=10000, watermark_col=None, watermark_val=None):
            yield [
                {"id": 1, "product": "Widget A", "price": 19.99, "updated_at": "2026-11-01T10:00:00"},
                {"id": 2, "product": "Widget B", "price": 49.50, "updated_at": "2026-11-02T11:00:00"},
            ]
            yield [
                {"id": 3, "product": "Widget C", "price": 99.00, "updated_at": "2026-11-03T12:00:00"},
            ]

        async def close(self):
            pass

    conn_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_conn = DataSourceConnection(
        id=conn_id,
        workspace_id=ws_id,
        created_by=user_id,
        name="Test Postgres",
        source_type="postgres",
        config={},
        encrypted_credentials="test",
        status="ready",
    )

    mock_db = AsyncMock()
    mock_result_conn = MagicMock()
    mock_result_conn.scalar_one_or_none.return_value = mock_conn

    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None
    mock_result_none.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [
        mock_result_conn,
        mock_result_none,
        mock_result_none,
    ]

    with (
        patch("app.services.connectors.import_engine.vault.decrypt", return_value={}),
        patch.object(ConnectorRegistry, "get", return_value=MockStreamingConnector(str(conn_id), {}, {})),
    ):
        import_record = await ImportEngine.execute_import(
            db=mock_db,
            connection_id=conn_id,
            resource_path="public.products",
            user_id=user_id,
            import_mode="incremental",
            watermark_column="updated_at",
        )

        assert import_record.status == "completed"
        assert import_record.rows_imported == 3
        assert import_record.bytes_imported > 0
        assert import_record.watermark_value == "2026-11-03T12:00:00"
        assert import_record.dataset_id is not None
        assert import_record.dataset_version_id is not None

        dataset_dir = tmp_path / "datasets" / str(ws_id) / str(import_record.dataset_id) / str(import_record.dataset_version_id) / "processed"
        assert dataset_dir.is_dir()
        manifest_file = dataset_dir / "manifest.json"
        assert manifest_file.is_file()
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest["row_count"] == 3
        assert len(manifest["parts"]) >= 1
        assert manifest["watermark_value"] == "2026-11-03T12:00:00"
