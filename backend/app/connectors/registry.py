"""Central Registry for DataLens External Data Source Connectors."""

from __future__ import annotations

from typing import Any

from app.connectors.base import BaseConnector
from app.connectors.exceptions import ConnectorError
from app.connectors.google_sheets.connector import GoogleSheetsConnector
from app.connectors.mongodb.connector import MongoDBConnector
from app.connectors.mysql.connector import MySQLConnector
from app.connectors.postgres.connector import PostgresConnector
from app.connectors.rest_api.connector import RestApiConnector
from app.connectors.s3.connector import S3Connector


class ConnectorRegistry:
    """Manages available connector implementations and instantiation."""

    _CONNECTORS: dict[str, type[BaseConnector]] = {
        "postgres": PostgresConnector,
        "mysql": MySQLConnector,
        "rest_api": RestApiConnector,
        "google_sheets": GoogleSheetsConnector,
        "mongodb": MongoDBConnector,
        "s3": S3Connector,
    }

    _METADATA: dict[str, dict[str, Any]] = {
        "postgres": {
            "type": "postgres",
            "name": "PostgreSQL",
            "category": "Relational Database",
            "icon": "database",
            "description": "Connect to PostgreSQL 12+ instances, Neon, Supabase, or RDS with SSL and streaming queries.",
            "default_port": 5432,
            "supports_watermark": True,
            "supports_ssl": True,
        },
        "mysql": {
            "type": "mysql",
            "name": "MySQL",
            "category": "Relational Database",
            "icon": "database",
            "description": "Connect to MySQL 8+ or MariaDB instances, PlanetScale, or RDS with server-side cursors.",
            "default_port": 3306,
            "supports_watermark": True,
            "supports_ssl": True,
        },
        "rest_api": {
            "type": "rest_api",
            "name": "REST API",
            "category": "Web Services & APIs",
            "icon": "globe",
            "description": "Ingest JSON data from any HTTP API with SSRF security, bearer/api-key auth, and auto-pagination.",
            "supports_watermark": True,
            "supports_ssl": True,
        },
        "google_sheets": {
            "type": "google_sheets",
            "name": "Google Sheets",
            "category": "Cloud Spreadsheets",
            "icon": "table",
            "description": "Direct OAuth 2.0 integration with Google Sheets API v4 to ingest tabular sheets and tabs.",
            "supports_watermark": True,
            "supports_ssl": True,
        },
        "mongodb": {
            "type": "mongodb",
            "name": "MongoDB",
            "category": "Document Database",
            "icon": "layers",
            "description": "Connect to MongoDB 5+ or Atlas clusters with BSON normalization and chunked cursor streaming.",
            "default_port": 27017,
            "supports_watermark": True,
            "supports_ssl": True,
        },
        "s3": {
            "type": "s3",
            "name": "S3-Compatible Storage",
            "category": "Object Storage",
            "icon": "archive",
            "description": "Connect to AWS S3, MinIO, Wasabi, or Cloudflare R2 buckets for CSV and Parquet ingestion.",
            "supports_watermark": True,
            "supports_ssl": True,
        },
    }

    @classmethod
    def register(cls, source_type: str, connector_cls: type[BaseConnector], metadata: dict[str, Any] | None = None) -> None:
        cls._CONNECTORS[source_type] = connector_cls
        if metadata:
            cls._METADATA[source_type] = metadata

    @classmethod
    def get(
        cls,
        source_type: str,
        connection_id: str,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> BaseConnector:
        source_key = source_type.lower()
        if source_key not in cls._CONNECTORS:
            raise ConnectorError(
                f"Unsupported data source type '{source_type}'. "
                f"Available connectors: {', '.join(cls._CONNECTORS.keys())}"
            )
        connector_cls = cls._CONNECTORS[source_key]
        return connector_cls(connection_id=connection_id, config=config, credentials=credentials)

    @classmethod
    def list_connectors(cls) -> list[dict[str, Any]]:
        return list(cls._METADATA.values())


registry = ConnectorRegistry
