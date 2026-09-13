"""Проверка ключа GigaChat из .env: список моделей и одна короткая реплика.

Запуск: make ai-check
"""

import asyncio
import sys

from core.config import get_settings
from infrastructure.ai.gigachat import GigaChatClient, GigaChatError, Message


async def main() -> int:
    settings = get_settings()
    if not settings.gigachat_enabled:
        print("FINIK_GIGACHAT_AUTH_KEY пуст. Вставь ключ авторизации в backend/.env")
        return 1
    client = GigaChatClient(settings)
    try:
        print("Модели:", ", ".join(await client.models()))
        reply = await client.complete(
            [
                Message(
                    "system", "Ты росток Финик из детской игры про деньги. Отвечай одной фразой."
                ),
                Message("user", "Привет! Я отложил 8 монет в копилку."),
            ],
            max_tokens=60,
        )
        print(f"Ответ {settings.gigachat_model}: {reply}")
        return 0
    except GigaChatError as exc:
        print("Ошибка:", exc)
        if "CERTIFICATE" in str(exc).upper():
            print("Похоже на сертификат: поставь FINIK_GIGACHAT_VERIFY_SSL=false для проверки")
        return 2
    finally:
        await client.aclose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
