"""Unit and integration tests for Phase 5A External Data Source Connectors."""

import json
from datetime import UTC

import pytest

from app.connectors.exceptions import SSRFSecurityError
from app.connectors.google_sheets.connector import GoogleSheetsConnector
from app.connectors.mongodb.connector import MongoDBConnector, normalize_bson
from app.connectors.mysql.connector import MySQLConnector
from app.connectors.postgres.connector import PostgresConnector
from app.connectors.registry import registry
from app.connectors.rest_api.connector import RestApiConnector, extract_records, flatten_json
from app.connectors.s3.connector import S3Connector
from app.connectors.security import CredentialVault, SSRFValidator, mask_credentials
from app.services.connectors.refresh_scheduler import RefreshSchedulerService

# ---------------------------------------------------------------------------
# 1. Credential Security & Masking Tests
# ---------------------------------------------------------------------------

def test_credential_vault_encrypt_decrypt():
    vault = CredentialVault(secret_key="test-secret-key-datalens-enterprise-5a")
    original = {
        "password": "SuperSecretPassword123!",
        "api_key": "live_key_987654321",
        "nested": {"token": "sub-token-value"},
    }
    encrypted = vault.encrypt(original)
    assert isinstance(encrypted, str)
    assert encrypted != json.dumps(original)

    # Decrypt
    decrypted = vault.decrypt(encrypted)
    assert decrypted == original


def test_credential_masking():
    data = {
        "host": "postgres.internal.com",
        "port": 5432,
        "database": "analytics",
        "password": "SecretPassword",
        "api_key": "live_api_key_12345",
        "user": {"token": "secret-token-xyz"},
    }
    masked = mask_credentials(data)
    assert masked["host"] == "postgres.internal.com"
    assert masked["port"] == 5432
    assert "Secret" not in masked["password"]
    assert "•" in masked["password"]
    assert "live_api" not in masked["api_key"]
    assert "•" in masked["user"]["token"]


# ---------------------------------------------------------------------------
# 2. SSRF Guard Tests
# ---------------------------------------------------------------------------

def test_ssrf_validator_blocks_private_and_loopback_ips():
    # Loopback
    with pytest.raises(SSRFSecurityError):
        SSRFValidator.validate_url("https://127.0.0.1:8080/data")

    with pytest.raises(SSRFSecurityError):
        SSRFValidator.validate_url("https://localhost/api")

    # Disallowed scheme
    with pytest.raises(SSRFSecurityError):
        SSRFValidator.validate_url("ftp://example.com/file")


def test_ssrf_validator_allows_safe_urls(monkeypatch):
    # Mock DNS resolution for public IP
    def fake_getaddrinfo(host, port, proto=0):
        return [(2, 1, 6, '', ('93.184.216.34', 443))]
    import socket
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    safe_url = SSRFValidator.validate_url("https://api.example.com/v1/data")
    assert safe_url == "https://api.example.com/v1/data"


# ---------------------------------------------------------------------------
# 3. Connector Registry Tests
# ---------------------------------------------------------------------------

def test_connector_registry_contains_all_six():
    all_connectors = registry.list_connectors()
    types = {c["type"] for c in all_connectors}
    expected = {"postgres", "mysql", "rest_api", "google_sheets", "mongodb", "s3"}
    assert expected.issubset(types)


def test_connector_instantiation():
    pg = registry.get("postgres", "c1", {"host": "localhost"}, {"password": "pass"})
    assert isinstance(pg, PostgresConnector)

    my = registry.get("mysql", "c2", {"host": "localhost"}, {"password": "pass"})
    assert isinstance(my, MySQLConnector)

    api = registry.get("rest_api", "c3", {"base_url": "https://api.com"}, {})
    assert isinstance(api, RestApiConnector)

    gs = registry.get("google_sheets", "c4", {"spreadsheet_id": "xyz"}, {})
    assert isinstance(gs, GoogleSheetsConnector)

    mg = registry.get("mongodb", "c5", {"host": "localhost"}, {})
    assert isinstance(mg, MongoDBConnector)

    s3 = registry.get("s3", "c6", {"bucket": "b1"}, {})
    assert isinstance(s3, S3Connector)


# ---------------------------------------------------------------------------
# 4. REST API Utilities & Connector Tests
# ---------------------------------------------------------------------------

def test_json_flattening():
    nested = {
        "id": 101,
        "customer": {"name": "Alice", "address": {"city": "New York"}},
        "tags": ["active", "vip"],
    }
    flat = flatten_json(nested)
    assert flat["id"] == 101
    assert flat["customer_name"] == "Alice"
    assert flat["customer_address_city"] == "New York"
    assert flat["tags"] == "active, vip"


def test_extract_records():
    payload = {
        "status": "ok",
        "data": {
            "items": [
                {"id": 1, "name": "Item A"},
                {"id": 2, "name": "Item B"},
            ]
        }
    }
    extracted = extract_records(payload, data_path="data.items")
    assert len(extracted) == 2
    assert extracted[0]["name"] == "Item A"


# ---------------------------------------------------------------------------
# 5. MongoDB BSON Normalization Tests
# ---------------------------------------------------------------------------

def test_bson_normalization():
    from datetime import datetime

    from bson import Decimal128, ObjectId

    dt = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
    oid = ObjectId()
    doc = {
        "_id": oid,
        "amount": Decimal128("199.99"),
        "created_at": dt,
        "meta": {"sub_id": ObjectId()},
    }
    normalized = normalize_bson(doc)
    assert normalized["_id"] == str(oid)
    assert normalized["amount"] == 199.99
    assert isinstance(normalized["created_at"], str)
    assert isinstance(normalized["meta"]["sub_id"], str)


# ---------------------------------------------------------------------------
# 6. Refresh Scheduler Service Tests
# ---------------------------------------------------------------------------

def test_refresh_scheduler_calculate_next_run():
    from datetime import datetime, timedelta
    base = datetime(2026, 11, 12, 12, 0, 0, tzinfo=UTC)

    next_hourly = RefreshSchedulerService.calculate_next_run("hourly", from_time=base)
    assert next_hourly == base + timedelta(hours=1)

    next_daily = RefreshSchedulerService.calculate_next_run("daily", from_time=base)
    assert next_daily == base + timedelta(days=1)

    next_weekly = RefreshSchedulerService.calculate_next_run("weekly", from_time=base)
    assert next_weekly == base + timedelta(weeks=1)

