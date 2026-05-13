"""Application configuration."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "iCare API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "iCare partner network backend"
    ENV: str = "dev"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:2148@localhost:5432/postgres"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Password policy
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False  # Optional for now

    # Observability
    # Log queries slower than this (milliseconds)
    SLOW_QUERY_THRESHOLD_MS: int = 1000
    HEALTH_CHECK_TIMEOUT_SECONDS: float = 5.0  # Timeout for DB health check

    # Security hardening
    BCRYPT_ROUNDS: int = 12  # Bcrypt cost factor (12 is recommended for 2024+)
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB max request body size
    MAX_STRING_LENGTH: int = 10000  # Max length for string fields
    ENABLE_DOCS_IN_PROD: bool = False  # Disable OpenAPI docs in production by default

    # OTP settings
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 3
    OTP_BLOCK_MINUTES: int = 15
    OTP_RESEND_LIMIT: int = 3
    OTP_RESEND_WINDOW_MINUTES: int = 15

    # Twilio (OTP delivery — leave empty in dev)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = ""
    TWILIO_SMS_FROM: str = ""


settings = Settings()
