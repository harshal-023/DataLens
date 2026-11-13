"""REST API Connector for DataLens with SSRF protection and pagination."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ConnectionAuthError,
    ConnectionTimeoutError,
    ConnectorError,
    QueryExecutionError,
    SSRFSecurityError,
)
from app.connectors.security import SSRFValidator


def flatten_json(data: Any, parent_key: str = "", sep: str = "_") -> dict[str, Any]:
    """Recursively flatten nested dictionary and arrays into flat key-value pairs."""
    items: dict[str, Any] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)
            if isinstance(v, dict):
                items.update(flatten_json(v, new_key, sep=sep))
            elif isinstance(v, list):
                # If list of primitives, join as comma-separated or stringify
                if all(not isinstance(i, (dict, list)) for i in v):
                    items[new_key] = ", ".join(str(i) for i in v)
                else:
                    items[new_key] = str(v)
            else:
                items[new_key] = v
    else:
        items[parent_key or "value"] = data
    return items


def extract_records(payload: Any, data_path: str | None = None) -> list[dict[str, Any]]:
    """Extract list of records from JSON payload according to optional dot-notation path."""
    current = payload
    if data_path:
        for part in data_path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return []

    if isinstance(current, list):
        return [flatten_json(item) if isinstance(item, dict) else {"value": item} for item in current]
    elif isinstance(current, dict):
        return [flatten_json(current)]
    return []


class RestApiConnector(BaseConnector):
    """Production REST API connector with SSRF security, rate-limiting, and multiple pagination strategies."""

    def __init__(
        self,
        connection_id: str,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> None:
        super().__init__(connection_id, config, credentials)
        self.base_url = self.config.get("base_url", "").rstrip("/")
        self.allow_http = bool(self.config.get("allow_http", False))
        self.allow_local = bool(self.config.get("allow_local", False))
        self.data_path = self.config.get("data_path")
        self.auth_type = self.config.get("auth_type", "none").lower()
        self.pagination_type = self.config.get("pagination_type", "none").lower()
        self.page_size = int(self.config.get("page_size", 100))
        self.rate_limit_delay = float(self.config.get("rate_limit_delay", 0.05))

    def _get_headers_and_auth(self) -> tuple[dict[str, str], httpx.Auth | None]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "DataLens-Connector/1.0",
        }
        # Add custom headers from config
        custom_headers = self.config.get("headers", {})
        if isinstance(custom_headers, dict):
            headers.update(custom_headers)

        auth: httpx.Auth | None = None

        if self.auth_type == "bearer":
            token = self.credentials.get("token") or self.credentials.get("api_key", "")
            headers["Authorization"] = f"Bearer {token}"
        elif self.auth_type == "api_key":
            api_key = self.credentials.get("api_key", "")
            header_name = self.config.get("api_key_header", "X-API-Key")
            headers[header_name] = api_key
        elif self.auth_type == "basic":
            user = self.credentials.get("username", "")
            pwd = self.credentials.get("password", "")
            auth = httpx.BasicAuth(user, pwd)

        return headers, auth

    def _validate_safe_url(self, url: str) -> str:
        return SSRFValidator.validate_url(
            url,
            allow_http=self.allow_http,
            allow_local=self.allow_local,
        )

    async def _make_request(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> httpx.Response:
        self._validate_safe_url(url)
        headers, auth = self._get_headers_and_auth()

        for attempt in range(max_retries):
            try:
                resp = await client.get(url, params=params, headers=headers, auth=auth, timeout=30.0)
                if resp.status_code == 429:  # Rate limited
                    retry_after = float(resp.headers.get("Retry-After", 2 ** attempt))
                    await asyncio.sleep(min(retry_after, 10.0))
                    continue
                if resp.status_code in (502, 503, 504) and attempt < max_retries - 1:
                    await asyncio.sleep(1.5 ** attempt)
                    continue
                if resp.status_code == 401 or resp.status_code == 403:
                    raise ConnectionAuthError(f"REST API authorization failed ({resp.status_code}): {resp.text[:200]}")
                resp.raise_for_status()
                return resp
            except httpx.TimeoutException as e:
                if attempt == max_retries - 1:
                    raise ConnectionTimeoutError(f"REST API request timed out: {str(e)}") from e
                await asyncio.sleep(1.0)
            except httpx.HTTPStatusError as e:
                raise QueryExecutionError(f"REST API request failed with status {e.response.status_code}: {e.response.text[:200]}") from e
            except SSRFSecurityError:
                raise
            except ConnectionAuthError:
                raise
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ConnectorError(f"HTTP request error: {str(e)}") from e
                await asyncio.sleep(1.0)

        raise ConnectorError("Max retries exceeded for REST API request.")

    async def test_connection(self) -> dict[str, Any]:
        start = time.perf_counter()
        test_endpoint = self.config.get("test_endpoint", "")
        url = f"{self.base_url}/{test_endpoint.lstrip('/')}" if test_endpoint else self.base_url

        async with httpx.AsyncClient() as client:
            resp = await self._make_request(client, url)
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "status": "success",
                "latency_ms": latency,
                "message": f"Successfully reached REST API ({resp.status_code} OK).",
                "server_version": resp.headers.get("Server", "Unknown"),
            }

    async def discover(self) -> dict[str, Any]:
        # Return configured endpoints or default root endpoint
        endpoints = self.config.get("endpoints", [])
        if not endpoints:
            endpoints = [{"name": "default", "path": self.config.get("data_endpoint", "")}]

        return {
            "base_url": self.base_url,
            "schemas": {"endpoints": endpoints},
            "total_tables": len(endpoints),
        }

    def _infer_column_type(self, val: Any) -> str:
        if isinstance(val, bool):
            return "BOOLEAN"
        elif isinstance(val, int):
            return "BIGINT"
        elif isinstance(val, float):
            return "DOUBLE"
        elif isinstance(val, dict):
            return "JSON"
        return "VARCHAR"

    async def get_schema(self, resource_path: str) -> list[dict[str, Any]]:
        preview_data = await self.preview(resource_path, limit=10)
        return preview_data.get("columns", [])

    async def preview(self, resource_path: str, limit: int = 100) -> dict[str, Any]:
        path = resource_path if resource_path and resource_path != "default" else self.config.get("data_endpoint", "")
        url = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url

        params = {}
        if self.pagination_type == "offset_limit":
            params["limit"] = min(limit, self.page_size)
            params["offset"] = 0
        elif self.pagination_type == "page":
            params["page"] = 1
            params["size"] = min(limit, self.page_size)

        async with httpx.AsyncClient() as client:
            resp = await self._make_request(client, url, params=params)
            try:
                payload = resp.json()
            except Exception as e:
                raise QueryExecutionError(f"REST API did not return valid JSON: {str(e)}") from e

            records = extract_records(payload, self.data_path)[:limit]
            
            # Infer columns from records
            col_map: dict[str, str] = {}
            for r in records:
                for k, v in r.items():
                    if k not in col_map or col_map[k] == "VARCHAR":
                        if v is not None:
                            col_map[k] = self._infer_column_type(v)

            columns = [
                {
                    "name": col,
                    "type": col_type,
                    "nullable": True,
                    "is_primary_key": col.lower() in ("id", "_id", "uuid"),
                }
                for col, col_type in col_map.items()
            ]

            return {
                "resource": resource_path,
                "columns": columns,
                "rows": records,
                "total_rows": len(records),
            }

    async def stream_data(
        self,
        resource_path: str,
        chunk_size: int = 10000,
        watermark_col: str | None = None,
        watermark_val: Any | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        path = resource_path if resource_path and resource_path != "default" else self.config.get("data_endpoint", "")
        url = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url

        offset = 0
        page = 1
        cursor_val = None
        has_more = True
        accumulated: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            while has_more:
                params: dict[str, Any] = {}
                if watermark_col and watermark_val is not None:
                    params[f"{watermark_col}_gt"] = watermark_val

                if self.pagination_type == "offset_limit":
                    params["offset"] = offset
                    params["limit"] = self.page_size
                elif self.pagination_type == "page":
                    params["page"] = page
                    params["page_size"] = self.page_size
                elif self.pagination_type == "cursor" and cursor_val:
                    params["cursor"] = cursor_val

                resp = await self._make_request(client, url, params=params)
                payload = resp.json()
                records = extract_records(payload, self.data_path)

                if not records:
                    break

                accumulated.extend(records)
                while len(accumulated) >= chunk_size:
                    yield accumulated[:chunk_size]
                    accumulated = accumulated[chunk_size:]

                # Update pagination state
                if self.pagination_type == "none" or len(records) < self.page_size:
                    has_more = False
                elif self.pagination_type == "offset_limit":
                    offset += len(records)
                elif self.pagination_type == "page":
                    page += 1
                elif self.pagination_type == "cursor":
                    # Look for cursor in payload
                    cursor_field = self.config.get("cursor_field", "next_cursor")
                    cursor_val = payload.get(cursor_field) if isinstance(payload, dict) else None
                    if not cursor_val:
                        has_more = False

                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)

            if accumulated:
                yield accumulated
