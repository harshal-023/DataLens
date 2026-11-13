import pytest
from pydantic import ValidationError

from app.core.exceptions import DataLensException
from app.schemas.auth import RegisterRequest
from app.services.auth_service import (
    check_login_rate_limit,
    clear_failed_logins,
    record_failed_login,
)
from app.services.email_adapter import dev_email_adapter


def test_password_policy_validation():
    # Valid strong password
    valid = RegisterRequest(
        full_name="Harshal Sharma",
        email="Harshal@DataLens.AI",
        password="SecurePassword2026!",
    )
    assert valid.email == "harshal@datalens.ai"  # Normalized to lowercase

    # Too short (< 8 chars)
    with pytest.raises(ValidationError):
        RegisterRequest(full_name="Test", email="test@test.com", password="Sh1!")

    # No uppercase letter
    with pytest.raises(ValidationError):
        RegisterRequest(full_name="Test", email="test@test.com", password="lowercaseonly123!")

    # No lowercase letter
    with pytest.raises(ValidationError):
        RegisterRequest(full_name="Test", email="test@test.com", password="UPPERCASEONLY123!")

    # No digit
    with pytest.raises(ValidationError):
        RegisterRequest(full_name="Test", email="test@test.com", password="NoDigitsAtAll!")


def test_login_rate_limiting():
    key = "attacker@test.com:127.0.0.1"
    clear_failed_logins(key)

    # 4 failed attempts should be allowed
    for _ in range(4):
        record_failed_login(key)
        check_login_rate_limit(key)

    # 5th failed attempt triggers rate limit
    record_failed_login(key)
    with pytest.raises(DataLensException) as exc_info:
        check_login_rate_limit(key)
    assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"

    clear_failed_logins(key)
    # Should be clear now
    check_login_rate_limit(key)


def test_dev_email_adapter():
    dev_email_adapter.clear()

    # Reset email
    reset_url = dev_email_adapter.send_password_reset("user@datalens.ai", "reset_token_xyz_123")
    assert "token=reset_token_xyz_123" in reset_url
    assert dev_email_adapter.get_latest_reset_token("user@datalens.ai") == "reset_token_xyz_123"

    # Invitation email
    invite_url = dev_email_adapter.send_workspace_invitation(
        to_email="colleague@datalens.ai",
        workspace_name="Analytics Core",
        invitation_token="invite_token_abc_789",
        inviter_name="Harshal Sharma",
    )
    assert "token=invite_token_abc_789" in invite_url
    assert dev_email_adapter.get_latest_invitation_token("colleague@datalens.ai") == "invite_token_abc_789"
