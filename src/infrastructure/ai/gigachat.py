"""Клиент GigaChat API.

Схема авторизации по документации developers.sber.ru:
1. POST /api/v2/oauth с заголовком Authorization: Basic <ключ авторизации> и полем scope
   отдаёт access_token на 30 минут. Ключ авторизации — Base64 от Client ID и Client Secret,
   готовая строка из личного кабинета.
2. Запросы к API идут с Bearer access_token на https://api.giga.chat/v1.
Токен кэшируется и обновляется за минуту до истечения.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from uuid import uuid4

import httpx

from core.config import Settings

log = logging.getLogger(__name__)


class GigaChatError(RuntimeError):
    """Провайдер недоступен или ответил ошибкой. Наверх поднимается только внутри ИИ-слоя."""


@dataclass(slots=True)
class Message:
    role: str  # system | user | assistant
    content: str


@dataclass(slots=True)
class _Token:
    value: str = ""
    expires_at: float = 0.0  # unix-секунды

    def valid(self) -> bool:
        return bool(self.value) and time.time() < self.expires_at - 60


@dataclass(slots=True)
class GigaChatClient:
    settings: Settings
    _token: _Token = field(default_factory=_Token)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=self.settings.gigachat_timeout_seconds,
                verify=self.settings.gigachat_verify_ssl,
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def access_token(self) -> str:
        async with self._lock:
            if self._token.valid():
                return self._token.value
            try:
                response = await self._client().post(
                    self.settings.gigachat_oauth_url,
                    headers={
                        "Authorization": f"Basic {self.settings.gigachat_auth_key}",
                        "RqUID": str(uuid4()),
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                    data={"scope": self.settings.gigachat_scope},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise GigaChatError(f"Не удалось получить токен GigaChat: {exc}") from exc
            payload = response.json()
            # expires_at приходит в миллисекундах unix-времени.
            self._token = _Token(payload["access_token"], payload["expires_at"] / 1000)
            return self._token.value

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 200,
        temperature: float | None = None,
    ) -> str:
        """Один ответ модели текстом. Стриминг не нужен: реплики короткие."""
        body: dict[str, object] = {
            "model": model or self.settings.gigachat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "stream": False,
        }
        if temperature is not None:
            body["temperature"] = temperature
        token = await self.access_token()
        try:
            response = await self._client().post(
                f"{self.settings.gigachat_api_url}/chat/completions",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                json=body,
            )
            if response.status_code == 401:  # токен отозвали раньше срока: один повтор
                self._token = _Token()
                token = await self.access_token()
                response = await self._client().post(
                    f"{self.settings.gigachat_api_url}/chat/completions",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                    json=body,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GigaChatError(f"GigaChat не ответил: {exc}") from exc
        data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise GigaChatError(f"Неожиданный ответ GigaChat: {data}") from exc

    async def models(self) -> list[str]:
        token = await self.access_token()
        response = await self._client().get(
            f"{self.settings.gigachat_api_url}/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return [str(m["id"]) for m in response.json().get("data", [])]
