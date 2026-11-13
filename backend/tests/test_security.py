import pytest

from app.core.security import hash_password, is_hash_rehash_needed, verify_password


def test_hash_and_verify_password():
    pwd = "EnterpriseSecurePassword#2026!"
    hashed = hash_password(pwd)

    # Argon2id hash verification
    assert hashed.startswith("$argon2id$")
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword#123", hashed) is False


def test_empty_password_rejection():
    with pytest.raises(ValueError):
        hash_password("")


def test_password_salting_uniqueness():
    pwd = "SamePassword123"
    hash1 = hash_password(pwd)
    hash2 = hash_password(pwd)

    # Different salts must yield different hashes
    assert hash1 != hash2
    assert verify_password(pwd, hash1) is True
    assert verify_password(pwd, hash2) is True


def test_rehash_check():
    pwd = "StandardPassword"
    hashed = hash_password(pwd)
    assert is_hash_rehash_needed(hashed) is False
    assert is_hash_rehash_needed("invalid_hash") is True
