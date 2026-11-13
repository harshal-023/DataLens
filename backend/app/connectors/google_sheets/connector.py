"""Google Sheets Connector for DataLens with OAuth 2.0 and token refresh."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ConnectionAuthError,
    ConnectionTimeoutError,
    QueryExecutionError,
    ResourceNotFoundError,
)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


class GoogleSheetsConnector(BaseConnector):
    """Production Google Sheets connector supporting OAuth 2.0, multi-sheet discovery, preview, and streaming."""

    def __init__(
        self,
        connection_id: str,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> None:
        super().__init__(connection_id, config, credentials)
        self.spreadsheet_id = self.config.get("spreadsheet_id", "")
        self.client_id = self.credentials.get("client_id", "")
        self.client_secret = self.credentials.get("client_secret", "")
        self.refresh_token = self.credentials.get("refresh_token", "")
        self.access_token = self.credentials.get("access_token", "")
        self.token_expiry = float(self.credentials.get("token_expiry", 0))

    async def _get_valid_access_token(self) -> str:
        """Returns valid access token, automatically refreshing it if expired."""
        now = time.time()
        if self.access_token and (self.token_expiry == 0 or now < (self.token_expiry - 60)):
            return self.access_token

        if not self.refresh_token:
            if self.access_token:
                return self.access_token
            raise ConnectionAuthError("Google Sheets credentials require a refresh_token or active access_token.")

        # Refresh token with Google OAuth
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=15.0,
                )
                if resp.status_code != 200:
                    raise ConnectionAuthError(f"Failed to refresh Google OAuth token ({resp.status_code}): {resp.text}")
                data = resp.json()
                self.access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self.token_expiry = time.time() + expires_in
                return self.access_token
            except ConnectionAuthError:
                raise
            except Exception as e:
                raise ConnectionAuthError(f"Error during Google OAuth token refresh: {str(e)}") from e

    async def _api_get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self._get_valid_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers, timeout=30.0)
                if resp.status_code == 401:
                    raise ConnectionAuthError(f"Google API authentication error: {resp.text}")
                if resp.status_code == 404:
                    raise ResourceNotFoundError(f"Google Spreadsheet or resource not found at {url}")
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException as e:
                raise ConnectionTimeoutError(f"Google API request timed out: {str(e)}") from e
            except ResourceNotFoundError:
                raise
            except ConnectionAuthError:
                raise
            except Exception as e:
                raise QueryExecutionError(f"Google Sheets API call failed: {str(e)}") from e

    async def test_connection(self) -> dict[str, Any]:
        start = time.perf_counter()
        if not self.spreadsheet_id:
            # Just test token validity
            _ = await self._get_valid_access_token()
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "status": "success",
                "latency_ms": latency,
                "message": "Google Sheets OAuth credentials verified successfully.",
            }

        url = f"{SHEETS_API_BASE}/{self.spreadsheet_id}"
        data = await self._api_get(url)
        title = data.get("properties", {}).get("title", "Untitled")
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "success",
            "latency_ms": latency,
            "message": f"Successfully connected to Google Sheet '{title}'.",
            "server_version": "Google Sheets API v4",
        }

    async def discover(self) -> dict[str, Any]:
        if not self.spreadsheet_id:
            raise ResourceNotFoundError("Spreadsheet ID must be provided in configuration to discover sheets.")

        url = f"{SHEETS_API_BASE}/{self.spreadsheet_id}"
        data = await self._api_get(url)
        title = data.get("properties", {}).get("title", "Untitled")
        sheets = data.get("sheets", [])

        sheet_list = []
        for s in sheets:
            props = s.get("properties", {})
            sheet_list.append({
                "name": props.get("title"),
                "sheet_id": props.get("sheetId"),
                "row_count": props.get("gridProperties", {}).get("rowCount", 0),
                "column_count": props.get("gridProperties", {}).get("columnCount", 0),
                "type": "SHEET",
            })

        return {
            "spreadsheet_id": self.spreadsheet_id,
            "title": title,
            "schemas": {"sheets": sheet_list},
            "total_tables": len(sheet_list),
        }

    def _infer_type(self, val: str) -> str:
        val_str = str(val).strip()
        if val_str.lower() in ("true", "false"):
            return "BOOLEAN"
        try:
            int(val_str)
            return "BIGINT"
        except ValueError:
            pass
        try:
            float(val_str)
            return "DOUBLE"
        except ValueError:
            pass
        return "VARCHAR"

    async def preview(self, resource_path: str, limit: int = 100) -> dict[str, Any]:
        sheet_name = resource_path or "Sheet1"
        safe_range = f"'{sheet_name}'!A1:ZZ{limit + 1}"
        url = f"{SHEETS_API_BASE}/{self.spreadsheet_id}/values/{safe_range}"
        
        data = await self._api_get(url, params={"valueRenderOption": "UNFORMATTED_VALUE"})
        values = data.get("values", [])
        if not values:
            return {"resource": resource_path, "columns": [], "rows": [], "total_rows": 0}

        headers = [str(h).strip() if str(h).strip() else f"col_{idx+1}" for idx, h in enumerate(values[0])]
        data_rows = values[1:]

        # Build column types and row dicts
        col_types: dict[str, str] = {h: "VARCHAR" for h in headers}
        rows: list[dict[str, Any]] = []

        for row_data in data_rows:
            row_dict: dict[str, Any] = {}
            for idx, h in enumerate(headers):
                cell_val = row_data[idx] if idx < len(row_data) else None
                row_dict[h] = cell_val
                if cell_val is not None and col_types[h] == "VARCHAR":
                    col_types[h] = self._infer_type(cell_val)
            rows.append(row_dict)

        columns = [
            {"name": h, "type": col_types[h], "nullable": True, "is_primary_key": idx == 0}
            for idx, h in enumerate(headers)
        ]

        return {
            "resource": sheet_name,
            "columns": columns,
            "rows": rows[:limit],
            "total_rows": len(rows),
        }

    async def get_schema(self, resource_path: str) -> list[dict[str, Any]]:
        preview_data = await self.preview(resource_path, limit=20)
        return preview_data.get("columns", [])

    async def stream_data(
        self,
        resource_path: str,
        chunk_size: int = 10000,
        watermark_col: str | None = None,
        watermark_val: Any | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        sheet_name = resource_path or "Sheet1"
        # Fetch the entire sheet values
        safe_range = f"'{sheet_name}'!A:ZZ"
        url = f"{SHEETS_API_BASE}/{self.spreadsheet_id}/values/{safe_range}"
        data = await self._api_get(url, params={"valueRenderOption": "UNFORMATTED_VALUE"})
        values = data.get("values", [])
        if not values or len(values) < 2:
            return

        headers = [str(h).strip() if str(h).strip() else f"col_{idx+1}" for idx, h in enumerate(values[0])]
        raw_rows = values[1:]

        batch: list[dict[str, Any]] = []
        for row_data in raw_rows:
            row_dict = {
                headers[idx]: (row_data[idx] if idx < len(row_data) else None)
                for idx in range(len(headers))
            }
            if watermark_col and watermark_val is not None:
                val = row_dict.get(watermark_col)
                if val is not None and str(val) <= str(watermark_val):
                    continue

            batch.append(row_dict)
            if len(batch) >= chunk_size:
                yield batch
                batch = []

        if batch:
            yield batch
