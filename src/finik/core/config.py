"""Настройки приложения. Единственный источник конфигурации — переменные окружения."""

from functools import lru_cache

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FINIK_", env_file=".env", extra="ignore")

    database_url: PostgresDsn = PostgresDsn("postgresql+asyncpg://localhost:5432/finik")
    jwt_secret: str = "change-me-in-production"
    jwt_ttl_days: int = 180
    debug: bool = True

    @property
    def database_dsn(self) -> str:
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
