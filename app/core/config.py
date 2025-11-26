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
    PROJECT_NAME: str = "FastAPI Backend Server"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A minimal, production-ready FastAPI server"
    ENV: str = "dev"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:2148@localhost:5432/postgres"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    CORS_ORIGINS: str | list[str] = "http://localhost:3000,http://localhost:8000"

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

    @model_validator(mode="before")
    @classmethod
    def parse_cors_origins(
        cls, values: dict[str, str | list[str]]
    ) -> dict[str, str | list[str]]:
        """Parse CORS origins from comma-separated string to list."""
        if "CORS_ORIGINS" in values and isinstance(values["CORS_ORIGINS"], str):
            values["CORS_ORIGINS"] = [
                origin.strip()
                for origin in values["CORS_ORIGINS"].split(",")
                if origin.strip()
            ]
        return values


settings = Settings()
