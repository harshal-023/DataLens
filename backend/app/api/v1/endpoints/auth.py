from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_secure_token
from app.db.session import get_db
from app.dependencies.auth import require_active_user, verify_csrf
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.schemas.common import SuccessEnvelope
from app.services.auth_service import AuthService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(response: Response, raw_refresh_token: str) -> str:
    """Sets secure HttpOnly refresh token cookie and CSRF token cookie."""
    csrf_token = generate_secure_token()

    # 1. HttpOnly Refresh Token Cookie
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
        path="/api/v1/auth",
    )

    # 2. CSRF Token Cookie (Readable by frontend client to populate X-CSRF-Token header)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
        path="/",
    )
    return csrf_token


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
    )
    response.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        path="/",
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Registers a new user, hashes password with Argon2id, and creates a default personal workspace.",
)
async def register(
    req: RegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user, workspace, token_resp, raw_refresh_token = await AuthService.register(req, db)
    _set_auth_cookies(response, raw_refresh_token)

    return AuthResponse(
        user=UserProfileResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            default_workspace_id=workspace.id,
        ),
        token=token_resp,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="User Authentication",
    description="Authenticates with email and password in constant time, returns access token, and sets HttpOnly refresh cookie.",
)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    user, token_resp, raw_refresh_token = await AuthService.login(
        req, db, ip_address=client_ip, user_agent=user_agent
    )
    _set_auth_cookies(response, raw_refresh_token)

    # Resolve default workspace ID
    workspaces = await WorkspaceService.list_user_workspaces(user.id, db)
    default_ws_id = workspaces[0].id if workspaces else None

    return AuthResponse(
        user=UserProfileResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            default_workspace_id=default_ws_id,
        ),
        token=token_resp,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Token Refresh with Rotation",
    description="Rotates refresh token and issues new access token. Detects and revokes token families on reuse.",
)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token_cookie: Annotated[str | None, Cookie(alias=settings.REFRESH_COOKIE_NAME)] = None,
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    token_resp, new_raw_refresh = await AuthService.refresh_session(
        raw_refresh_token=refresh_token_cookie or "",
        db=db,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    _set_auth_cookies(response, new_raw_refresh)
    return token_resp


@router.post(
    "/logout",
    response_model=SuccessEnvelope[dict],
    dependencies=[Depends(verify_csrf)],
    summary="User Logout",
    description="Revokes current refresh session and clears authentication cookies.",
)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token_cookie: Annotated[str | None, Cookie(alias=settings.REFRESH_COOKIE_NAME)] = None,
):
    await AuthService.logout(refresh_token_cookie, db)
    _clear_auth_cookies(response)
    return SuccessEnvelope(data={"logged_out": True}, message="Successfully logged out.")


@router.post(
    "/logout-all",
    response_model=SuccessEnvelope[dict],
    summary="Revoke All Sessions",
    description="Revokes all active refresh sessions across all browsers for current user.",
)
async def logout_all(
    response: Response,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await AuthService.logout_all(current_user.id, db)
    _clear_auth_cookies(response)
    return SuccessEnvelope(data={"revoked_all": True}, message="All active sessions have been terminated.")


@router.get(
    "/me",
    response_model=SuccessEnvelope[dict],
    summary="Current User Profile",
    description="Returns authenticated user profile and associated workspaces.",
)
async def get_me(
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    workspaces = await WorkspaceService.list_user_workspaces(current_user.id, db)
    default_ws_id = workspaces[0].id if workspaces else None

    user_data = UserProfileResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        default_workspace_id=default_ws_id,
    )

    return SuccessEnvelope(
        data={
            "user": user_data,
            "workspaces": workspaces,
        }
    )


@router.post(
    "/change-password",
    response_model=SuccessEnvelope[dict],
    summary="Change Password",
    description="Validates current password, updates to new Argon2id hash, and revokes all active sessions.",
)
async def change_password(
    req: ChangePasswordRequest,
    response: Response,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await AuthService.change_password(current_user, req, db)
    _clear_auth_cookies(response)
    return SuccessEnvelope(
        data={"password_changed": True},
        message="Password updated successfully. Please log in with your new password.",
    )


@router.post(
    "/forgot-password",
    response_model=SuccessEnvelope[dict],
    summary="Forgot Password",
    description="Issues a cryptographically secure single-use password reset link via email adapter.",
)
async def forgot_password(
    req: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await AuthService.forgot_password(req.email, db)
    return SuccessEnvelope(
        data={"sent": True},
        message="If this email is registered, password reset instructions have been dispatched.",
    )


@router.post(
    "/reset-password",
    response_model=SuccessEnvelope[dict],
    summary="Reset Password with Token",
    description="Applies new password using valid reset token and invalidates token.",
)
async def reset_password(
    req: ResetPasswordRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await AuthService.reset_password(req, db)
    _clear_auth_cookies(response)
    return SuccessEnvelope(
        data={"reset_successful": True},
        message="Password has been reset successfully. Please log in with your new password.",
    )
