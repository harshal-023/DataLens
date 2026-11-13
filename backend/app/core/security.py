import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

# Configure Argon2id password hasher
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hashes a raw plaintext password using Argon2id."""
    if not password:
        raise ValueError("Password cannot be empty.")
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash in constant time."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def is_hash_rehash_needed(hashed_password: str) -> bool:
    """Checks if an existing hash needs rehashing due to parameter updates."""
    try:
        return _ph.check_needs_rehash(hashed_password)
    except Exception:
        return True


# ==========================================
# JWT ACCESS TOKEN MANAGEMENT
# ==========================================

def create_access_token(
    user_id: uuid.UUID | str,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Creates a signed, short-lived JWT access token.
    Uses HS256 algorithm with application SECRET_KEY.
    """
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email.strip().lower(),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT access token.
    Enforces algorithm restrictions, signature verification, and expiration check.
    Raises jwt.PyJWTError subclasses on invalid tokens.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "exp", "type"]},
    )


# ==========================================
# SECURE RANDOM TOKENS & OPAQUE TOKEN HASHING
# ==========================================

def generate_secure_token(nbytes: int = 32) -> str:
    """Generates a cryptographically secure, URL-safe random string."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """
    Computes SHA-256 hash of an opaque token (refresh token, reset token, invitation token).
    Only the hash is persisted in PostgreSQL to protect against database leaks.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
