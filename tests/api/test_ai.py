"""Точки ИИ: заготовки без модели, кэш и стоплист с подставной моделью."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from api.deps import get_llm
from application.use_cases import ai as use_ai
from domain.entities import ShopItem
from domain.enums import Category
from domain.services.quiz import build_questions
from main import create_app


class ScriptedLlm:
    enabled = True

    def __init__(self, text: str = "Мне хорошо. Давай спрячем монеты в мечту.") -> None:
        self.text = text
        self.calls: list[tuple[str, str]] = []

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 160,
        temperature: float | None = None,
    ) -> str | None:
        self.calls.append((system, user))
        return self.text


async def start(client: AsyncClient) -> dict[str, str]:
    r = await client.post("/api/v1/auth/device", json={"device_id": f"test-{uuid4()}"})
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    r = await client.post(
        "/api/v1/pet",
        headers=headers,
        json={"name": "Кустик", "species": "FINIK", "weekly_income": 40},
    )
    assert r.status_code == 201
    return headers


@asynccontextmanager
async def llm_client(llm: ScriptedLlm) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_llm] = lambda: llm
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_fallback_endpoints(client: AsyncClient):
    h = await start(client)
    state = (await client.get("/api/v1/state", headers=h)).json()
    assert "Кустик" in state["pet"]["mood_note"]

    r = await client.get("/api/v1/ai/remark", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "fallback" and body["text"]

    r = await client.get("/api/v1/ai/word-of-day", headers=h)
    assert r.status_code == 200
    assert r.json()["word"] and r.json()["meaning"]

    r = await client.get("/api/v1/ai/diary", headers=h)
    assert r.status_code == 200 and "день" in r.json()["text"].lower()

    r = await client.get("/api/v1/ai/dream-plan", headers=h)
    plan = r.json()
    assert plan["remain"] == 150 and plan["weekly_save"] == 8
    assert plan["weeks_left"] == 19
    assert plan["steps"][0]["coins"] == 8
    assert plan["cut_play"] == 2 and plan["weeks_saved"] == 4
    assert "2" in plan["advice"] and "4" in plan["advice"]

    r = await client.get("/api/v1/ai/origin", headers=h)
    assert r.status_code == 200
    assert len([p for p in r.json()["text"].split("\n\n") if p.strip()]) == 3

    r = await client.get("/api/v1/ai/quiz", headers=h)
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert 1 <= len(qs) <= 3 and "right_index" not in qs[0]

    r = await client.get("/api/v1/ai/week-summary", headers=h)
    assert r.status_code == 404

    r = await client.post("/api/v1/ai/chat", headers=h, json={"text": "Что такое копилка?"})
    assert r.status_code == 200
    assert r.json()["source"] == "fallback" and r.json()["chat_left"] == 11

    r = await client.post(
        "/api/v1/ai/chat", headers=h, json={"text": "номер карты 4111111111111111"}
    )
    assert r.json()["blocked"] is True and "копилк" in r.json()["text"].lower()


async def test_week_story_persists(client: AsyncClient):
    h = await start(client)
    for _ in range(7):
        await client.post("/api/v1/day/end", headers=h)
    r = await client.get("/api/v1/ai/week-summary", headers=h)
    assert r.status_code == 200
    text = r.json()["text"]
    assert r.json()["source"] == "fallback" and r.json()["week_number"] == 1
    r = await client.get("/api/v1/ai/week-summary", headers=h)
    assert r.json()["source"] == "cache" and r.json()["text"] == text
    history = (await client.get("/api/v1/weeks/history", headers=h)).json()
    assert history["last_story"] == text


async def test_llm_remark_is_cached():
    llm = ScriptedLlm("Я доволен. Давай ещё чуть в копилку.")
    async with llm_client(llm) as client:
        h = await start(client)
        first = await client.get("/api/v1/ai/remark", headers=h)
        second = await client.get("/api/v1/ai/remark", headers=h)
        assert first.json()["source"] == "llm"
        assert second.json()["source"] == "cache"
        assert first.json()["text"] == second.json()["text"] == llm.text
        assert len(llm.calls) == 1


async def test_unsafe_model_output_falls_back():
    llm = ScriptedLlm("Сходи на https://evil.test за монетами")
    async with llm_client(llm) as client:
        h = await start(client)
        r = await client.get("/api/v1/ai/remark", headers=h)
        assert r.json()["source"] == "fallback"
        assert "evil" not in r.json()["text"]


async def test_chat_daily_limit(monkeypatch):
    monkeypatch.setattr(use_ai.rules, "AI_CHAT_PER_DAY", 2)
    llm = ScriptedLlm("Копилка только на мечту.")
    async with llm_client(llm) as client:
        h = await start(client)
        r = await client.post("/api/v1/ai/chat", headers=h, json={"text": "зачем копилка?"})
        assert r.json()["source"] == "llm" and r.json()["chat_left"] == 1
        await client.post("/api/v1/ai/chat", headers=h, json={"text": "а скидка?"})
        r = await client.post("/api/v1/ai/chat", headers=h, json={"text": "ещё вопрос"})
        assert r.json()["chat_left"] == 0 and "завтра" in r.json()["text"].lower()
        assert len(llm.calls) == 2


async def test_word_of_day_is_global():
    llm = ScriptedLlm("Росток спрятал монеты в копилку.")
    async with llm_client(llm) as client:
        h1 = await start(client)
        r = await client.post("/api/v1/auth/device", json={"device_id": f"test-{uuid4()}"})
        h2 = {"Authorization": f"Bearer {r.json()['token']}"}
        await client.post(
            "/api/v1/pet",
            headers=h2,
            json={"name": "Искорка", "species": "SPARK", "weekly_income": 20},
        )
        first = await client.get("/api/v1/ai/word-of-day", headers=h1)
        second = await client.get("/api/v1/ai/word-of-day", headers=h2)
        assert first.json()["source"] == "llm"
        assert second.json()["source"] == "cache"
        assert first.json()["example"] == second.json()["example"] == llm.text
        assert first.json()["word"] == second.json()["word"]
        assert len(llm.calls) == 1


async def test_shop_quiz_reward_once(client: AsyncClient):
    h = await start(client)
    quiz = (await client.get("/api/v1/ai/quiz", headers=h)).json()
    assert quiz["kind"] == "quiz" and quiz["questions"]
    state = (await client.get("/api/v1/state", headers=h)).json()
    shelf = (await client.get("/api/v1/shop/items", headers=h)).json()
    items = [
        ShopItem(i["slug"], i["name"], Category(i["category"]), i["cost"], i["old_cost"], "G")
        for i in shelf
    ]
    built = build_questions(items, "quiz", f"{state['week']['id']}:{state['week']['day']}:quiz")
    r = await client.post(
        "/api/v1/ai/quiz/answer",
        headers=h,
        json={"index": 0, "answer_index": built[0].right_index, "kind": "quiz"},
    )
    assert r.status_code == 200 and r.json()["correct"] is True and r.json()["coins"] == 2
    r = await client.post(
        "/api/v1/ai/quiz/answer",
        headers=h,
        json={"index": 1, "answer_index": built[1].right_index, "kind": "quiz"},
    )
    assert r.json()["correct"] is True and r.json()["coins"] == 0
    r = await client.post(
        "/api/v1/ai/quiz/answer",
        headers=h,
        json={"index": 0, "answer_index": built[0].right_index, "kind": "quiz"},
    )
    assert r.status_code == 422
