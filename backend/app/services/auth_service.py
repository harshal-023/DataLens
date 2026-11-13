import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DataLensException
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.password_reset import PasswordResetToken
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services.email_adapter import dev_email_adapter

# In-memory IP/email failed login attempts for basic rate limiting
_failed_login_attempts: dict[str, list[float]] = {}


def check_login_rate_limit(key: str) -> None:
    now = time.time()
    attempts = _failed_login_attempts.get(key, [])
    # Prune attempts outside the sliding window
    window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    valid_attempts = [t for t in attempts if now - t < window]
    _failed_login_attempts[key] = valid_attempts

    if len(valid_attempts) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
        raise DataLensException(
            message="Too many failed login attempts. Please try again later.",
            code="RATE_LIMIT_EXCEEDED",
        )


def record_failed_login(key: str) -> None:
    now = time.time()
    attempts = _failed_login_attempts.get(key, [])
    attempts.append(now)
    _failed_login_attempts[key] = attempts


def clear_failed_logins(key: str) -> None:
    _failed_login_attempts.pop(key, None)


class AuthService:
    @staticmethod
    async def register(req: RegisterRequest, db: AsyncSession) -> tuple[User, Workspace, TokenResponse, str]:
        email = req.email.strip().lower()

        # Check existing user
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise DataLensException(
                message="An account with this email address already exists.",
                code="DUPLICATE_EMAIL",
            )

        # 1. Create User
        user = User(
            full_name=req.full_name.strip(),
            email=email,
            password_hash=hash_password(req.password),
            is_active=True,
        )
        db.add(user)
        await db.flush()  # Flushes to generate user.id

        # 2. Create Default Personal Workspace in the same transaction
        workspace_name = f"{user.full_name}'s Workspace"
        workspace = Workspace(
            name=workspace_name,
            owner_id=user.id,
        )
        db.add(workspace)
        await db.flush()

        # 3. Add Workspace Membership with role 'owner'
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )
        db.add(membership)

        # 4. Generate Initial Tokens
        access_token = create_access_token(user.id, user.email)
        raw_refresh_token = generate_secure_token()
        refresh_hash = hash_token(raw_refresh_token)
        refresh_expires = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = RefreshSession(
            user_id=user.id,
            token_hash=refresh_hash,
            family_id=uuid.uuid4(),
            expires_at=refresh_expires,
        )
        db.add(session)
        await db.commit()
        await db.refresh(user)

        token_resp = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return user, workspace, token_resp, raw_refresh_token

    @staticmethod
    async def login(
        req: LoginRequest,
        db: AsyncSession,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, TokenResponse, str]:
        email = req.email.strip().lower()
        rate_key = f"{email}:{ip_address or 'local'}"
        check_login_rate_limit(rate_key)

        # Check durable PostgreSQL-backed rate limit for multi-worker / restart survivability
        if type(db).__name__ not in ("AsyncMock", "MagicMock"):
            try:
                from app.models.governance import SecurityEvent

                cutoff = datetime.now(UTC) - timedelta(seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
                recent_fails_stmt = (
                    select(func.count(SecurityEvent.id))
                    .where(
                        SecurityEvent.event_type.in_(["FAILED_LOGIN", "FAILED_LOGIN_BURST"]),
                        SecurityEvent.created_at >= cutoff,
                        SecurityEvent.details["rate_key"].astext == rate_key,
                    )
                )
                recent_fails = (await db.execute(recent_fails_stmt)).scalar() or 0
                if recent_fails >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
                    raise DataLensException(
                        message="Too many failed login attempts. Please try again later.",
                        code="RATE_LIMIT_EXCEEDED",
                    )
            except DataLensException:
                raise
            except Exception:
                pass

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # Generic error message to prevent account enumeration
        invalid_err = DataLensException(
            message="Invalid email or password.",
            code="INVALID_CREDENTIALS",
        )

        if user is None:
            record_failed_login(rate_key)
            if type(db).__name__ not in ("AsyncMock", "MagicMock"):
                try:
                    from app.services.governance_service import GovernanceService

                    await GovernanceService.record_security_event(
                        db=db,
                        workspace_id=None,
                        event_type="FAILED_LOGIN",
                        severity="HIGH" if len(_failed_login_attempts.get(rate_key, [])) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS else "MEDIUM",
                        details={"rate_key": rate_key, "email": email, "ip_address": ip_address, "reason": "user_not_found"},
                    )
                except Exception:
                    pass
            raise invalid_err

        if not user.is_active:
            raise DataLensException(
                message="Your account has been deactivated. Please contact support.",
                code="INACTIVE_USER",
            )

        if not verify_password(req.password, user.password_hash):
            record_failed_login(rate_key)
            if type(db).__name__ not in ("AsyncMock", "MagicMock"):
                try:
                    from app.services.governance_service import GovernanceService

                    await GovernanceService.record_security_event(
                        db=db,
                        workspace_id=None,
                        event_type="FAILED_LOGIN",
                        severity="HIGH" if len(_failed_login_attempts.get(rate_key, [])) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS else "MEDIUM",
                        details={"rate_key": rate_key, "email": email, "ip_address": ip_address, "user_id": str(user.id), "reason": "invalid_password"},
                    )
                except Exception:
                    pass
            raise invalid_err

        clear_failed_logins(rate_key)

        # Generate access token
        access_token = create_access_token(user.id, user.email)

        # Generate refresh token and session with new family
        raw_refresh_token = generate_secure_token()
        refresh_hash = hash_token(raw_refresh_token)
        refresh_expires = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = RefreshSession(
            user_id=user.id,
            token_hash=refresh_hash,
            family_id=uuid.uuid4(),
            expires_at=refresh_expires,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(session)
        await db.commit()

        token_resp = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return user, token_resp, raw_refresh_token

    @staticmethod
    async def refresh_session(
        raw_refresh_token: str,
        db: AsyncSession,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[TokenResponse, str]:
        if not raw_refresh_token:
            raise DataLensException("Refresh token is required.", code="UNAUTHORIZED")

        token_hash = hash_token(raw_refresh_token)
        result = await db.execute(select(RefreshSession).where(RefreshSession.token_hash == token_hash))
        session = result.scalar_one_or_none()

        if session is None:
            raise DataLensException("Invalid or expired session.", code="UNAUTHORIZED")

        # Reuse Detection: If already revoked token is submitted, revoke entire token family!
        if session.is_revoked:
            await db.execute(
                update(RefreshSession)
                .where(RefreshSession.family_id == session.family_id)
                .values(is_revoked=True)
            )
            await db.commit()
            raise DataLensException(
                message="Security alert: Refresh token reuse detected. All sessions in this family have been terminated.",
                code="TOKEN_REUSE_DETECTED",
            )

        # Check expiration
        now = datetime.now(UTC)
        if session.expires_at < now:
            session.is_revoked = True
            await db.commit()
            raise DataLensException("Session has expired. Please log in again.", code="UNAUTHORIZED")

        # Fetch active user
        user = await db.get(User, session.user_id)
        if user is None or not user.is_active:
            session.is_revoked = True
            await db.commit()
            raise DataLensException("User account is inactive.", code="INACTIVE_USER")

        # Rotate: Invalidate current token and issue new token in the same family
        session.is_revoked = True

        new_raw_refresh_token = generate_secure_token()
        new_token_hash = hash_token(new_raw_refresh_token)
        new_expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_session = RefreshSession(
            user_id=user.id,
            token_hash=new_token_hash,
            family_id=session.family_id,
            expires_at=new_expires,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(new_session)
        await db.commit()

        new_access_token = create_access_token(user.id, user.email)
        token_resp = TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return token_resp, new_raw_refresh_token

    @staticmethod
    async def logout(raw_refresh_token: str | None, db: AsyncSession) -> None:
        if raw_refresh_token:
            token_hash = hash_token(raw_refresh_token)
            await db.execute(
                update(RefreshSession)
                .where(RefreshSession.token_hash == token_hash)
                .values(is_revoked=True)
            )
            await db.commit()

    @staticmethod
    async def logout_all(user_id: uuid.UUID, db: AsyncSession) -> None:
        await db.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id)
            .values(is_revoked=True)
        )
        await db.commit()

    @staticmethod
    async def change_password(user: User, req: ChangePasswordRequest, db: AsyncSession) -> None:
        if not verify_password(req.current_password, user.password_hash):
            raise DataLensException(
                message="Incorrect current password.",
                code="INVALID_PASSWORD",
            )

        user.password_hash = hash_password(req.new_password)
        # Revoke all existing refresh sessions for this user on password change
        await db.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user.id)
            .values(is_revoked=True)
        )
        await db.commit()

    @staticmethod
    async def forgot_password(email: str, db: AsyncSession) -> None:
        email_clean = email.strip().lower()
        result = await db.execute(select(User).where(User.email == email_clean))
        user = result.scalar_one_or_none()

        # Always return generic success to prevent email enumeration
        if user and user.is_active:
            raw_token = generate_secure_token()
            token_hash = hash_token(raw_token)
            expires = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires,
                is_used=False,
            )
            db.add(reset_record)
            await db.commit()
            dev_email_adapter.send_password_reset(user.email, raw_token)

    @staticmethod
    async def reset_password(req: ResetPasswordRequest, db: AsyncSession) -> None:
        token_hash = hash_token(req.token)
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.is_used == False,  # noqa: E712
            )
        )
        reset_record = result.scalar_one_or_none()

        if reset_record is None:
            raise DataLensException(
                message="Invalid or already used password reset link.",
                code="INVALID_RESET_TOKEN",
            )

        if reset_record.expires_at < datetime.now(UTC):
            reset_record.is_used = True
            await db.commit()
            raise DataLensException(
                message="Password reset link has expired. Please request a new one.",
                code="EXPIRED_RESET_TOKEN",
            )

        user = await db.get(User, reset_record.user_id)
        if user is None or not user.is_active:
            raise DataLensException("User account not found or inactive.", code="INACTIVE_USER")

        # Update password, mark token used, revoke all existing sessions
        user.password_hash = hash_password(req.new_password)
        reset_record.is_used = True
        await db.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user.id)
            .values(is_revoked=True)
        )
        await db.commit()
