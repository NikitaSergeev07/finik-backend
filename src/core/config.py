"""Настройки приложения. Единственный источник конфигурации — переменные окружения."""

from functools import lru_cache

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FINIK_", env_file=".env", extra="ignore")

    database_url: PostgresDsn = PostgresDsn("postgresql+asyncpg://localhost:5432/finik")
    jwt_secret: str = "change-me-in-production-please-use-32-bytes"
    jwt_ttl_days: int = 180
    debug: bool = True

    # GigaChat. Ключ авторизации берётся в Studio: проект GigaChat API → Настройки API →
    # Получить ключ. Показывается один раз. Scope для физлиц GIGACHAT_API_PERS.
    gigachat_auth_key: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat"
    gigachat_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_api_url: str = "https://api.giga.chat/v1"
    gigachat_verify_ssl: bool = True
    gigachat_timeout_seconds: float = 20.0

    @property
    def gigachat_enabled(self) -> bool:
        return bool(self.gigachat_auth_key)

    @property
    def database_dsn(self) -> str:
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
