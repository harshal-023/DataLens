from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(Path(__file__).resolve().parent.parent.parent / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "DataLens API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # PostgreSQL Asynchronous Connection String
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/datalens"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True

    # CORS configuration
    CORS_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Security & Tokens
    SECRET_KEY: str = "datalens_dev_secret_key_replace_with_strong_random_value_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7    # 7-day refresh tokens
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    INVITATION_TOKEN_EXPIRE_DAYS: int = 7

    # Cookie & CSRF Security
    COOKIE_SECURE: bool = False  # Set to True automatically in production
    COOKIE_SAMESITE: str = "lax"
    REFRESH_COOKIE_NAME: str = "datalens_refresh_token"
    CSRF_COOKIE_NAME: str = "datalens_csrf_token"

    # Rate Limiting
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Storage Abstraction Configuration
    STORAGE_ROOT: str = "./storage_data"
    MAX_UPLOAD_SIZE_MB: int = 50

    @property
    def STORAGE_LOCAL_ROOT(self) -> str:
        return self.STORAGE_ROOT

    # AI Provider Configuration (Unified Gemini + Ollama + Hybrid Routing)
    AI_PROVIDER: str = "gemini"
    AI_ROUTING_MODE: str = "HYBRID"  # GEMINI_ONLY, LOCAL_ONLY, HYBRID, DETERMINISTIC_ONLY
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    AI_API_KEY: str | None = None  # Backward-compatible fallback
    AI_MODEL: str = "gemini-3.5-flash"
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 2
    AI_ENABLED: bool = True
    AI_SEND_SAMPLE_VALUES: bool = False  # Privacy default: zero raw cell data sent to AI provider

    # Local AI (Ollama) Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"
    OLLAMA_TIMEOUT_SECONDS: int = 60
    OLLAMA_TEMPERATURE: float = 0.1

    @property
    def effective_ai_api_key(self) -> str | None:
        return self.GEMINI_API_KEY or self.AI_API_KEY

    @property
    def effective_ai_model(self) -> str:
        return self.GEMINI_MODEL or self.AI_MODEL or "gemini-3.5-flash"


    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore
        raise ValueError(v)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_production_secret(cls, v: str, info) -> str:
        data = info.data
        if data.get("APP_ENV") == "production":
            if "dev_secret" in v or len(v) < 32:
                raise ValueError("SECRET_KEY must be a cryptographically secure random string of at least 32 characters in production.")
        return v

    @field_validator("COOKIE_SECURE")
    @classmethod
    def set_production_cookie_secure(cls, v: bool, info) -> bool:
        data = info.data
        if data.get("APP_ENV") == "production":
            return True
        return v


settings = Settings()
