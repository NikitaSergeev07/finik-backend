"""Клиент GigaChat как порт LlmGateway. Сбой проглатывается: наверх уходит None."""

from __future__ import annotations

import logging

from core.config import Settings
from infrastructure.ai.deepseek import DeepSeekGateway
from infrastructure.ai.gigachat import GigaChatClient, GigaChatError, Message

log = logging.getLogger(__name__)


class SilentLlm:
    """Нет ключа — сценарии сразу берут заготовку, без ожидания сети."""

    enabled = False

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 160,
        temperature: float | None = None,
    ) -> str | None:
        return None


class GigaChatGateway:
    def __init__(self, client: GigaChatClient) -> None:
        self._client = client
        self.enabled = True

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 160,
        temperature: float | None = None,
    ) -> str | None:
        try:
            return await self._client.complete(
                [Message("system", system), Message("user", user)],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except GigaChatError:
            log.warning("GigaChat не ответил, берём заготовку", exc_info=True)
            return None

    async def aclose(self) -> None:
        await self._client.aclose()


def build_llm(settings: Settings) -> SilentLlm | GigaChatGateway | DeepSeekGateway:
    if settings.llm_provider == "deepseek":
        return DeepSeekGateway(settings) if settings.deepseek_enabled else SilentLlm()
    if settings.llm_provider == "gigachat":
        if settings.gigachat_enabled:
            return GigaChatGateway(GigaChatClient(settings))
        return SilentLlm()
    if settings.gigachat_enabled:
        return GigaChatGateway(GigaChatClient(settings))
    if settings.deepseek_enabled:
        return DeepSeekGateway(settings)
    return SilentLlm()
