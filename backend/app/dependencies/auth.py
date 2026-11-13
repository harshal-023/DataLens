import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.permissions import normalize_role
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.services.workspace_service import WorkspaceService

# Security scheme for Swagger UI & OpenAPI spec
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Validates JWT access token from Authorization: Bearer <token>
    and loads the authenticated user from the database.
    """
    if not cred or not cred.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Please refresh your session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

    user = await db.get(User, user_uuid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found.")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


async def require_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )
    return current_user


async def get_current_workspace(
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_workspace_id: Annotated[str | None, Header()] = None,
) -> tuple[Workspace, str]:
    """
    Resolves the workspace context for the current request.
    Extracts workspace ID from 'X-Workspace-ID' header.
    Verifies user membership and returns (Workspace, user_role).
    """
    if not x_workspace_id:
        # Fallback to the user's first available workspace
        workspaces = await WorkspaceService.list_user_workspaces(current_user.id, db)
        if not workspaces:
            raise DataLensException("User does not belong to any workspace.", code="NOT_FOUND")
        target_ws_id = workspaces[0].id
    else:
        try:
            target_ws_id = uuid.UUID(x_workspace_id)
        except ValueError:
            raise DataLensException("Invalid X-Workspace-ID format.", code="BAD_REQUEST")

    return await WorkspaceService.get_workspace(target_ws_id, current_user.id, db)


def require_workspace_role(allowed_roles: list[str]) -> Callable:
    """
    Dependency factory that checks if the caller's role in the current workspace
    matches one of the allowed_roles.
    """
    normalized_allowed = [normalize_role(r) for r in allowed_roles]

    async def _role_checker(
        ws_context: Annotated[tuple[Workspace, str], Depends(get_current_workspace)],
    ) -> tuple[Workspace, str]:
        workspace, role = ws_context
        if normalize_role(role) not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action not permitted. Requires one of roles: {', '.join(normalized_allowed)}.",
            )
        return workspace, role

    return _role_checker


def verify_csrf(
    request: Request,
    csrf_token_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=settings.CSRF_COOKIE_NAME)] = None,
) -> None:
    """
    Double-submit CSRF verification for state-changing requests using cookie authentication.
    Safe methods (GET, HEAD, OPTIONS) bypass verification.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # If request is authenticated with an explicit Authorization header, CSRF is not required
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return

    if not csrf_token_header or not csrf_cookie or csrf_token_header != csrf_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed.",
        )
