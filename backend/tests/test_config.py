import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_config_defaults():
    settings = Settings()
    assert settings.APP_NAME == "DataLens API"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert isinstance(settings.CORS_ORIGINS, list)
    assert settings.MAX_UPLOAD_SIZE_MB == 50
    assert settings.STORAGE_ROOT == "./storage_data"


def test_cors_origins_parsing():
    settings = Settings(CORS_ORIGINS="http://example.com, https://app.datalens.ai")
    assert "http://example.com" in settings.CORS_ORIGINS
    assert "https://app.datalens.ai" in settings.CORS_ORIGINS


def test_production_secret_key_validation():
    # In production, default dev secret or short secret must raise ValidationError
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SECRET_KEY="datalens_dev_secret_key_replace_with_strong_random_value_in_production",
        )

    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SECRET_KEY="too_short_secret",
        )

    # Valid production secret with 32+ characters and no dev_secret string should succeed
    valid_prod = Settings(
        APP_ENV="production",
        SECRET_KEY="c2VjdXJlX3Byb2R1Y3Rpb25fa2V5X2ZvcmludGVncmF0aW9uXzIwMjY=",
    )
    assert valid_prod.APP_ENV == "production"
