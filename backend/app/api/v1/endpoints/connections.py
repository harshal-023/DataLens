"""FastAPI endpoints for external data source connections, imports, and refreshes."""

from __future__ import annotations

import urllib.parse
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.exceptions import ConnectorError
from app.connectors.registry import ConnectorRegistry
from app.connectors.security import mask_credentials, vault
from app.core.exceptions import DataLensException
from app.db.session import get_db
from app.dependencies.auth import require_active_user, require_workspace_role
from app.models.data_source import (
    DataSourceConnection,
    DataSourceImport,
    DataSourceRefreshConfig,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.data_source import (
    ColumnMetadataItem,
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    ConnectionUpdate,
    DiscoveryResponse,
    GoogleAuthCallbackRequest,
    GoogleAuthUrlResponse,
    ImportRequest,
    ImportResponse,
    PreviewRequest,
    PreviewResponse,
    RefreshConfigCreate,
    RefreshConfigResponse,
    TableSchemaResponse,
)
from app.services.connectors.import_engine import ImportEngine
from app.services.connectors.refresh_scheduler import RefreshSchedulerService

router = APIRouter(prefix="/connections", tags=["External Data Sources"])


# ---------------------------------------------------------------------------
# Metadata & Testing
# ---------------------------------------------------------------------------

@router.get("/connectors", response_model=list[dict[str, Any]])
async def list_available_connectors(
    current_user: Annotated[User, Depends(require_active_user)],
):
    """List all supported external connector types and capabilities."""
    return ConnectorRegistry.list_connectors()


@router.post("/test", response_model=ConnectionTestResponse)
async def test_connection_on_the_fly(
    req: ConnectionTestRequest,
    current_user: Annotated[User, Depends(require_active_user)],
):
    """Test connection credentials and reachability before saving."""
    try:
        connector = ConnectorRegistry.get(
            source_type=req.source_type,
            connection_id="test",
            config=req.config,
            credentials=req.credentials,
        )
        res = await connector.test_connection()
        await connector.close()
        return ConnectionTestResponse(**res)
    except ConnectorError as e:
        return ConnectionTestResponse(
            status="failed",
            latency_ms=0.0,
            message=f"Connection failed: {e.message}",
            server_version=None,
        )
    except Exception as e:
        return ConnectionTestResponse(
            status="failed",
            latency_ms=0.0,
            message=f"Connection error: {str(e)}",
            server_version=None,
        )


# ---------------------------------------------------------------------------
# Google OAuth Endpoints
# ---------------------------------------------------------------------------

@router.get("/oauth/google/auth-url", response_model=GoogleAuthUrlResponse)
async def get_google_auth_url(
    current_user: Annotated[User, Depends(require_active_user)],
    client_id: Annotated[str, Query()],
    redirect_uri: Annotated[str, Query()],
):
    """Generate OAuth 2.0 authorization URL for Google Sheets integration."""
    state = str(uuid.uuid4())
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/spreadsheets.readonly https://www.googleapis.com/auth/drive.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    encoded = urllib.parse.urlencode(params)
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{encoded}"
    return GoogleAuthUrlResponse(auth_url=auth_url, state=state)


@router.post("/oauth/google/callback", response_model=dict[str, Any])
async def handle_google_oauth_callback(
    req: GoogleAuthCallbackRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    client_id: Annotated[str, Query()],
    client_secret: Annotated[str, Query()],
    redirect_uri: Annotated[str, Query()],
):
    """Exchange OAuth authorization code for Google access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": req.code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15.0,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth token exchange failed: {resp.text}",
            )
        data = resp.json()
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "token_type": data.get("token_type"),
        }


# ---------------------------------------------------------------------------
# Connection CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ConnectionResponse])
async def list_connections(
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all data source connections in current workspace."""
    workspace, _ = ws_context
    stmt = (
        select(DataSourceConnection)
        .where(DataSourceConnection.workspace_id == workspace.id)
        .order_by(desc(DataSourceConnection.created_at))
    )
    res = await db.execute(stmt)
    conns = res.scalars().all()
    # Mask configs and ensure no credentials leaked
    out = []
    for c in conns:
        c_dict = {
            "id": c.id,
            "workspace_id": c.workspace_id,
            "name": c.name,
            "source_type": c.source_type,
            "config": mask_credentials(c.config),
            "status": c.status,
            "last_tested_at": c.last_tested_at,
            "is_active": c.is_active,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        out.append(ConnectionResponse(**c_dict))
    return out


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    req: ConnectionCreate,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new external data source connection with encrypted credentials."""
    workspace, _ = ws_context

    # Encrypt secrets via CredentialVault
    encrypted_creds = vault.encrypt(req.credentials)

    new_conn = DataSourceConnection(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        created_by=current_user.id,
        name=req.name.strip(),
        source_type=req.source_type.lower(),
        config=req.config,
        encrypted_credentials=encrypted_creds,
        status="configured",
        is_active=req.is_active,
    )
    db.add(new_conn)
    await db.commit()
    await db.refresh(new_conn)

    return ConnectionResponse(
        id=new_conn.id,
        workspace_id=new_conn.workspace_id,
        name=new_conn.name,
        source_type=new_conn.source_type,
        config=mask_credentials(new_conn.config),
        status=new_conn.status,
        last_tested_at=new_conn.last_tested_at,
        is_active=new_conn.is_active,
        created_at=new_conn.created_at,
        updated_at=new_conn.updated_at,
    )


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get single connection metadata (secrets masked)."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    return ConnectionResponse(
        id=conn.id,
        workspace_id=conn.workspace_id,
        name=conn.name,
        source_type=conn.source_type,
        config=mask_credentials(conn.config),
        status=conn.status,
        last_tested_at=conn.last_tested_at,
        is_active=conn.is_active,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )


@router.put("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: uuid.UUID,
    req: ConnectionUpdate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update connection name, config, or rotated credentials."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    if req.name is not None:
        conn.name = req.name.strip()
    if req.config is not None:
        conn.config = req.config
    if req.credentials is not None and len(req.credentials) > 0:
        # Re-encrypt
        conn.encrypted_credentials = vault.encrypt(req.credentials)
    if req.is_active is not None:
        conn.is_active = req.is_active

    conn.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(conn)

    return ConnectionResponse(
        id=conn.id,
        workspace_id=conn.workspace_id,
        name=conn.name,
        source_type=conn.source_type,
        config=mask_credentials(conn.config),
        status=conn.status,
        last_tested_at=conn.last_tested_at,
        is_active=conn.is_active,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a data source connection."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    await db.delete(conn)
    await db.commit()
    return None


@router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
async def test_saved_connection(
    connection_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Test an existing saved connection using its stored encrypted credentials."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    creds = vault.decrypt(conn.encrypted_credentials)
    try:
        connector = ConnectorRegistry.get(conn.source_type, str(conn.id), conn.config, creds)
        test_res = await connector.test_connection()
        await connector.close()

        conn.last_tested_at = datetime.now(UTC)
        conn.status = "ready"
        await db.commit()

        return ConnectionTestResponse(**test_res)
    except Exception as e:
        conn.status = "error"
        await db.commit()
        return ConnectionTestResponse(
            status="failed",
            latency_ms=0.0,
            message=f"Test failed: {str(e)}",
            server_version=None,
        )


# ---------------------------------------------------------------------------
# Discovery & Exploration
# ---------------------------------------------------------------------------

@router.get("/{connection_id}/discover", response_model=DiscoveryResponse)
async def discover_resources(
    connection_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Discover databases, schemas, tables, collections, files or sheets."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    creds = vault.decrypt(conn.encrypted_credentials)
    connector = ConnectorRegistry.get(conn.source_type, str(conn.id), conn.config, creds)
    try:
        data = await connector.discover()
        return DiscoveryResponse(**data)
    except ConnectorError as e:
        raise HTTPException(status_code=400, detail=e.message)
    finally:
        await connector.close()


@router.get("/{connection_id}/schema", response_model=TableSchemaResponse)
async def get_resource_schema(
    connection_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    resource_path: Annotated[str, Query(description="Table name, collection name, or object key")],
):
    """Get column schema and types for a specific resource."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    creds = vault.decrypt(conn.encrypted_credentials)
    connector = ConnectorRegistry.get(conn.source_type, str(conn.id), conn.config, creds)
    try:
        columns = await connector.get_schema(resource_path)
        col_items = [ColumnMetadataItem(**c) for c in columns]
        return TableSchemaResponse(resource=resource_path, columns=col_items)
    except ConnectorError as e:
        raise HTTPException(status_code=400, detail=e.message)
    finally:
        await connector.close()


@router.post("/{connection_id}/preview", response_model=PreviewResponse)
async def preview_resource(
    connection_id: uuid.UUID,
    req: PreviewRequest,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Preview records/rows from a specific table, sheet, collection or file."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    creds = vault.decrypt(conn.encrypted_credentials)
    connector = ConnectorRegistry.get(conn.source_type, str(conn.id), conn.config, creds)
    try:
        preview_data = await connector.preview(req.resource_path, limit=req.limit)
        col_items = [ColumnMetadataItem(**c) for c in preview_data.get("columns", [])]
        return PreviewResponse(
            resource=preview_data.get("resource", req.resource_path),
            columns=col_items,
            rows=preview_data.get("rows", []),
            total_rows=preview_data.get("total_rows", 0),
        )
    except ConnectorError as e:
        raise HTTPException(status_code=400, detail=e.message)
    finally:
        await connector.close()


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

@router.post("/{connection_id}/imports", response_model=ImportResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_import(
    connection_id: uuid.UUID,
    req: ImportRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Trigger data extraction and ingestion from source into immutable Parquet dataset."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        import_record = await ImportEngine.execute_import(
            db=db,
            connection_id=conn.id,
            resource_path=req.resource_path,
            user_id=current_user.id,
            import_mode=req.import_mode,
            target_dataset_name=req.target_dataset_name,
            target_dataset_id=req.target_dataset_id,
            watermark_column=req.watermark_column,
        )
        return ImportResponse.model_validate(import_record)
    except DataLensException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{connection_id}/imports", response_model=list[ImportResponse])
async def list_imports(
    connection_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List historical imports for a connection."""
    workspace, _ = ws_context
    stmt = (
        select(DataSourceImport)
        .where(
            DataSourceImport.connection_id == connection_id,
            DataSourceImport.workspace_id == workspace.id,
        )
        .order_by(desc(DataSourceImport.started_at))
    )
    res = await db.execute(stmt)
    imports = res.scalars().all()
    return [ImportResponse.model_validate(i) for i in imports]


@router.get("/{connection_id}/imports/{import_id}", response_model=ImportResponse)
async def get_import_details(
    connection_id: uuid.UUID,
    import_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get status and details of a specific import."""
    workspace, _ = ws_context
    stmt = select(DataSourceImport).where(
        DataSourceImport.id == import_id,
        DataSourceImport.connection_id == connection_id,
        DataSourceImport.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    imp = res.scalar_one_or_none()
    if not imp:
        raise HTTPException(status_code=404, detail="Import record not found")
    return ImportResponse.model_validate(imp)


@router.post("/{connection_id}/imports/{import_id}/cancel", response_model=ImportResponse)
async def cancel_import(
    connection_id: uuid.UUID,
    import_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mark an in-progress import as cancelled."""
    workspace, _ = ws_context
    stmt = select(DataSourceImport).where(
        DataSourceImport.id == import_id,
        DataSourceImport.connection_id == connection_id,
        DataSourceImport.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    imp = res.scalar_one_or_none()
    if not imp:
        raise HTTPException(status_code=404, detail="Import record not found")

    if imp.status == "in_progress":
        imp.status = "cancelled"
        imp.completed_at = datetime.now(UTC)
        imp.error_message = "Cancelled by user"
        await db.commit()

    return ImportResponse.model_validate(imp)


# ---------------------------------------------------------------------------
# Refresh & Schedules
# ---------------------------------------------------------------------------

@router.post("/{connection_id}/refresh", response_model=ImportResponse)
async def trigger_manual_refresh(
    connection_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_active_user)],
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Execute an immediate manual refresh using the latest active refresh configuration."""
    workspace, _ = ws_context
    # Find active refresh config
    cfg_stmt = (
        select(DataSourceRefreshConfig)
        .where(
            DataSourceRefreshConfig.connection_id == connection_id,
            DataSourceRefreshConfig.is_active.is_(True),
        )
        .order_by(desc(DataSourceRefreshConfig.created_at))
    )
    cfg_res = await db.execute(cfg_stmt)
    cfg = cfg_res.scalar_one_or_none()

    if not cfg:
        # Fallback to latest import config
        latest_imp_stmt = (
            select(DataSourceImport)
            .where(DataSourceImport.connection_id == connection_id)
            .order_by(desc(DataSourceImport.started_at))
        )
        latest_res = await db.execute(latest_imp_stmt)
        latest_imp = latest_res.scalar_one_or_none()
        if not latest_imp:
            raise HTTPException(status_code=400, detail="No refresh configuration or previous import found to refresh.")
        target_resource = latest_imp.source_resource
        import_mode = latest_imp.import_mode
        dataset_id = latest_imp.dataset_id
        watermark_column = latest_imp.watermark_column
    else:
        target_resource = cfg.target_resource
        import_mode = cfg.refresh_mode
        dataset_id = cfg.dataset_id
        watermark_column = cfg.watermark_column

    imp_record = await ImportEngine.execute_import(
        db=db,
        connection_id=connection_id,
        resource_path=target_resource,
        user_id=current_user.id,
        import_mode=import_mode,
        target_dataset_id=dataset_id,
        watermark_column=watermark_column,
    )
    return ImportResponse.model_validate(imp_record)


@router.get("/{connection_id}/refresh-config", response_model=list[RefreshConfigResponse])
async def get_refresh_configs(
    connection_id: uuid.UUID,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor", "viewer"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get scheduled refresh configurations for this connection."""
    workspace, _ = ws_context
    stmt = (
        select(DataSourceRefreshConfig)
        .where(DataSourceRefreshConfig.connection_id == connection_id)
        .order_by(desc(DataSourceRefreshConfig.created_at))
    )
    res = await db.execute(stmt)
    configs = res.scalars().all()
    return [RefreshConfigResponse.model_validate(c) for c in configs]


@router.post("/{connection_id}/refresh-config", response_model=RefreshConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_refresh_config(
    connection_id: uuid.UUID,
    req: RefreshConfigCreate,
    ws_context: Annotated[
        tuple[Workspace, str],
        Depends(require_workspace_role(["owner", "admin", "editor"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create or replace a scheduled refresh configuration."""
    workspace, _ = ws_context
    stmt = select(DataSourceConnection).where(
        DataSourceConnection.id == connection_id,
        DataSourceConnection.workspace_id == workspace.id,
    )
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    next_run = RefreshSchedulerService.calculate_next_run(
        frequency=req.frequency,
        cron_expression=req.cron_expression,
    )

    new_cfg = DataSourceRefreshConfig(
        id=uuid.uuid4(),
        connection_id=conn.id,
        dataset_id=req.dataset_id,
        frequency=req.frequency,
        cron_expression=req.cron_expression,
        refresh_mode=req.refresh_mode,
        target_resource=req.target_resource,
        watermark_column=req.watermark_column,
        timezone=req.timezone,
        is_active=req.is_active,
        next_run_at=next_run,
    )
    db.add(new_cfg)
    await db.commit()
    await db.refresh(new_cfg)

    return RefreshConfigResponse.model_validate(new_cfg)
