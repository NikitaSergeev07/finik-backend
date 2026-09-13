"""Клиент GigaChat без сети: OAuth, кэш токена, повтор при 401."""

import json
import time

import httpx
import pytest

from core.config import Settings
from infrastructure.ai.gigachat import GigaChatClient, GigaChatError, Message


def make_client(handler) -> GigaChatClient:
    settings = Settings(gigachat_auth_key="dGVzdA==", database_url="postgresql+asyncpg://x/y")
    client = GigaChatClient(settings)
    client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


async def test_token_is_cached_and_used():
    calls = {"oauth": 0, "chat": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth"):
            calls["oauth"] += 1
            assert request.headers["Authorization"] == "Basic dGVzdA=="
            assert "RqUID" in request.headers
            return httpx.Response(
                200, json={"access_token": "tok", "expires_at": (time.time() + 1800) * 1000}
            )
        calls["chat"] += 1
        assert request.headers["Authorization"] == "Bearer tok"
        body = json.loads(request.content)
        assert body["model"] == "GigaChat"
        if calls["chat"] == 1:
            assert body["messages"][0]["role"] == "system"
        return httpx.Response(200, json={"choices": [{"message": {"content": " Привет! "}}]})

    client = make_client(handler)
    reply = await client.complete([Message("system", "s"), Message("user", "u")])
    await client.complete([Message("user", "u")])
    assert reply == "Привет!"
    assert calls == {"oauth": 1, "chat": 2}


async def test_retries_once_on_401():
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth"):
            return httpx.Response(
                200,
                json={"access_token": f"t{state['n']}", "expires_at": (time.time() + 1800) * 1000},
            )
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(401)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ок"}}]})

    client = make_client(handler)
    assert await client.complete([Message("user", "u")]) == "ок"


async def test_oauth_failure_is_wrapped():
    client = make_client(lambda r: httpx.Response(500))
    with pytest.raises(GigaChatError):
        await client.complete([Message("user", "u")])
