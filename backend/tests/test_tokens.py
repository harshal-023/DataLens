import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_token,
)


def test_create_and_decode_access_token():
    user_id = uuid.uuid4()
    email = "harshal@datalens.ai"

    token = create_access_token(user_id=user_id, email=email)
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_expired_access_token_rejection():
    user_id = uuid.uuid4()
    email = "expired@datalens.ai"

    # Create token that expired 10 seconds ago
    expired_token = create_access_token(
        user_id=user_id,
        email=email,
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_tampered_token_signature_rejection():
    token = create_access_token(user_id=uuid.uuid4(), email="valid@datalens.ai")

    # Tamper with token signature
    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.tampered_signature"

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered_token)


def test_algorithm_restriction_enforcement():
    # Attempt decoding with wrong algorithm
    user_id = str(uuid.uuid4())
    fake_token = jwt.encode(
        {"sub": user_id, "type": "access", "exp": 9999999999},
        "wrong_secret",
        algorithm="HS384",
    )

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(fake_token)


def test_secure_random_token_and_sha256_hash():
    token1 = generate_secure_token(32)
    token2 = generate_secure_token(32)

    assert token1 != token2
    assert len(token1) >= 40  # URL-safe representation of 32 bytes

    hash1 = hash_token(token1)
    hash2 = hash_token(token2)

    assert hash1 != hash2
    assert len(hash1) == 64  # SHA-256 hexadecimal string is exactly 64 characters
    # Deterministic hash for same input
    assert hash_token(token1) == hash1
