from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL

Environment = Literal["dev", "test", "prod"]


def _build_sync_dsn(settings: "Settings") -> str:
    return str(
        URL.create(
            drivername="postgresql",
            username=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
        )
    )


def _build_async_dsn(settings: "Settings") -> str:
    return str(
        URL.create(
            drivername="postgresql+asyncpg",
            username=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
        )
    )


class Settings(BaseSettings):
    app_name: str = Field(default="SCP API", validation_alias="APP_NAME")
    app_env: Environment = Field(default="dev", validation_alias="APP_ENV")
    secret_key: str = Field(default="change-me", validation_alias="SECRET_KEY", min_length=8)
    access_token_expire_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALG")

    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="scp", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="scp", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="scp", validation_alias="POSTGRES_PASSWORD")

    cors_origins: list[str] = Field(default_factory=list, validation_alias="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def environment(self) -> Environment:
        return self.app_env

    @property
    def async_database_url(self) -> str:
        return _build_async_dsn(self)

    @property
    def sync_database_url(self) -> str:
        return _build_sync_dsn(self)

    @property
    def debug(self) -> bool:
        return self.app_env == "dev"

    @property
    def version(self) -> str:
        return "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
