"""Checks for the AI branch adapter without creating a database."""

import httpx
import pytest

from api.schemas.ai import QuizQuestionOut
from core.config import Settings
from infrastructure.ai.deepseek import DeepSeekGateway
from infrastructure.ai.gateway import GigaChatGateway, SilentLlm, build_llm
from main import create_app


def test_provider_selection() -> None:
    empty = Settings(_env_file=None, gigachat_auth_key="", deepseek_api_key="")
    assert isinstance(build_llm(empty), SilentLlm)

    giga = Settings(_env_file=None, gigachat_auth_key="test", deepseek_api_key="test")
    assert isinstance(build_llm(giga), GigaChatGateway)

    deepseek = Settings(
        _env_file=None,
        llm_provider="deepseek",
        gigachat_auth_key="test",
        deepseek_api_key="test",
    )
    gateway = build_llm(deepseek)
    assert isinstance(gateway, DeepSeekGateway)


@pytest.mark.asyncio
async def test_deepseek_gateway_uses_configured_key_and_handles_failure() -> None:
    settings = Settings(_env_file=None, deepseek_api_key="test-key")
    gateway = DeepSeekGateway(settings)
    await gateway.aclose()

    requests: list[httpx.Request] = []

    def success(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Привет!"}}]})

    gateway._client = httpx.AsyncClient(
        transport=httpx.MockTransport(success),
        base_url=settings.deepseek_api_url.rstrip("/") + "/",
        headers={"Authorization": "Bearer test-key"},
    )
    try:
        answer = await gateway.complete(system="Роль", user="Вопрос", max_tokens=42)
        assert answer == "Привет!"
        assert requests[0].url.path == "/chat/completions"
        assert requests[0].headers["Authorization"] == "Bearer test-key"
    finally:
        await gateway.aclose()

    gateway._client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(503)),
        base_url=settings.deepseek_api_url.rstrip("/") + "/",
    )
    try:
        assert await gateway.complete(system="Роль", user="Вопрос") is None
    finally:
        await gateway.aclose()


@pytest.mark.asyncio
async def test_daily_quiz_requires_token_and_hides_answer() -> None:
    app = create_app()
    routes = app.openapi()["paths"]
    operation = routes["/api/v1/quiz/daily"]["get"]
    assert operation["security"]
    assert "right_index" not in QuizQuestionOut.model_fields
    assert "correct_option_index" not in QuizQuestionOut.model_fields

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/quiz/daily")
    assert response.status_code == 401
