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
    gigachat_model: str = "GigaChat-3-Lightning"
    gigachat_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_api_url: str = "https://api.giga.chat/v1"
    gigachat_verify_ssl: bool = True
    # Путь к корневому сертификату Минцифры (PEM). Если задан, проверка идёт по нему.
    gigachat_ca_bundle: str = "certs/russian_trusted_root_ca.pem"
    gigachat_timeout_seconds: float = 8.0
    parent_pin: str = "1234"

    @property
    def gigachat_enabled(self) -> bool:
        return bool(self.gigachat_auth_key)

    @property
    def gigachat_verify(self) -> bool | str:
        """Что передать httpx в verify: путь к CA, если файл есть, иначе флаг."""
        from pathlib import Path

        if self.gigachat_verify_ssl and self.gigachat_ca_bundle:
            path = Path(self.gigachat_ca_bundle)
            if path.is_file():
                return str(path)
        return self.gigachat_verify_ssl

    @property
    def database_dsn(self) -> str:
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
