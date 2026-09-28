"""DeepSeek adapter for the application's LlmGateway protocol."""

import logging

import httpx

from core.config import Settings

log = logging.getLogger(__name__)


class DeepSeekGateway:
    enabled = True

    def __init__(self, settings: Settings) -> None:
        self._model = settings.deepseek_model
        self._client = httpx.AsyncClient(
            base_url=settings.deepseek_api_url.rstrip("/") + "/",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            timeout=settings.deepseek_timeout_seconds,
        )

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 160,
        temperature: float | None = None,
    ) -> str | None:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        try:
            response = await self._client.post("chat/completions", json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            log.warning("DeepSeek did not answer; using fallback", exc_info=True)
            return None
        if not isinstance(content, str):
            return None
        return content.strip() or None

    async def aclose(self) -> None:
        await self._client.aclose()
