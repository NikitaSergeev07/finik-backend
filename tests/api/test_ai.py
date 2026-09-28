"""Точки ИИ: заготовки без модели, кэш и стоплист с подставной моделью."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

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


async def test_lesson_hint_keeps_answer_hidden_and_caches() -> None:
    llm = ScriptedLlm("А что изменилось в цене после скидки?")
    async with llm_client(llm) as client:
        headers = await start(client)
        question = (await client.get(
            "/api/v1/tasks/lesson_discount/questions", headers=headers
        )).json()[0]
        request = {"question_slug": question["slug"]}
        before = await client.post(
            "/api/v1/tasks/lesson_discount/hint", headers=headers, json=request
        )
        assert before.status_code == 422
        await client.post(
            "/api/v1/tasks/lesson_discount/answer", headers=headers,
            json={**request, "answer_index": 0},
        )
        first = await client.post(
            "/api/v1/tasks/lesson_discount/hint", headers=headers, json=request
        )
        second = await client.post(
            "/api/v1/tasks/lesson_discount/hint", headers=headers, json=request
        )
        assert first.json()["source"] == "llm"
        assert second.json()["source"] == "cache"
        assert first.json()["text"] == second.json()["text"]
        assert len(llm.calls) == 1


async def test_lesson_hint_rejects_answer_from_model() -> None:
    llm = ScriptedLlm("Правильный ответ: 6 монет.")
    async with llm_client(llm) as client:
        headers = await start(client)
        question = (await client.get(
            "/api/v1/tasks/lesson_discount/questions", headers=headers
        )).json()[0]
        await client.post(
            "/api/v1/tasks/lesson_discount/answer", headers=headers,
            json={"question_slug": question["slug"], "answer_index": 0},
        )
        response = await client.post(
            "/api/v1/tasks/lesson_discount/hint", headers=headers,
            json={"question_slug": question["slug"]},
        )
        assert response.json()["source"] == "fallback"
        assert "6" not in response.json()["text"]


async def test_adventure_reaction_is_cached() -> None:
    llm = ScriptedLlm("Я рад, что мы заранее подумали о запасе.")
    async with llm_client(llm) as client:
        headers = await start(client)
        url = "/api/v1/adventures/adventure_market"
        first = await client.post(
            f"{url}/play", headers=headers,
            json={"expected_stage": 0, "food": 6, "water": 4, "reserve": 6},
        )
        resumed = await client.get(url, headers=headers)
        assert first.json()["pet_reaction"] == llm.text
        assert resumed.json()["pet_reaction"] == llm.text
        assert len(llm.calls) == 1


async def test_origin_keeps_three_model_paragraphs():
    llm = ScriptedLlm("Я лиса и нашла монету.\n\nЯ берегу воду.\n\nТеперь коплю на мечту.")
    async with llm_client(llm) as client:
        h = await start(client)
        response = await client.get("/api/v1/ai/origin", headers=h)
        assert response.status_code == 200
        assert response.json()["source"] == "llm"
        assert response.json()["text"].count("\n\n") == 2


async def test_off_topic_chat_redirect_does_not_spend_limit():
    llm = ScriptedLlm()
    async with llm_client(llm) as client:
        h = await start(client)
        response = await client.post(
            "/api/v1/ai/chat", headers=h, json={"text": "Какая сегодня погода?"}
        )
        assert response.json()["blocked"] is True
        assert not llm.calls
        next_reply = await client.post(
            "/api/v1/ai/chat", headers=h, json={"text": "Зачем нужна копилка?"}
        )
        assert next_reply.json()["chat_left"] == 11


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
    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    built = build_questions(items, "quiz", f"{state['pet']['id']}:{today}:quiz")
    r = await client.post(
        "/api/v1/ai/quiz/answer",
        headers=h,
        json={"index": 0, "answer_index": built[0].right_index, "kind": "quiz"},
    )
    assert r.status_code == 200 and r.json()["correct"] is True and r.json()["coins"] == 2
    progressed = (await client.get("/api/v1/ai/quiz", headers=h)).json()
    assert progressed["answered"] == [0] and progressed["rewarded"] is True
    await client.post("/api/v1/day/end", headers=h)
    same_calendar_day = (await client.get("/api/v1/ai/quiz", headers=h)).json()
    assert same_calendar_day["answered"] == [0]
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


async def test_price_quiz_rotates_on_calendar_day(client: AsyncClient, monkeypatch):
    base = datetime(2026, 9, 28, 12)

    class Clock(datetime):
        day_offset = 0

        @classmethod
        def now(cls, tz=None):
            return (base + timedelta(days=cls.day_offset)).replace(tzinfo=tz)

    monkeypatch.setattr(use_ai, "datetime", Clock)
    h = await start(client)
    first = (await client.get("/api/v1/ai/quiz", headers=h)).json()
    assert first["answered"] == []
    answer = await client.post(
        "/api/v1/ai/quiz/answer",
        headers=h,
        json={"index": 0, "answer_index": 0, "kind": "quiz"},
    )
    assert answer.status_code == 200
    assert (await client.get("/api/v1/ai/quiz", headers=h)).json()["answered"] == [0]

    Clock.day_offset = 1
    second = (await client.get("/api/v1/ai/quiz", headers=h)).json()
    assert second["answered"] == []
    assert second["rewarded"] is False


async def test_price_explanation_requires_answer_and_uses_model():
    llm = ScriptedLlm("Разложи монеты рядом с товарами и сравни кучки.")
    async with llm_client(llm) as client:
        h = await start(client)
        await client.get("/api/v1/ai/quiz", headers=h)
        early = await client.get("/api/v1/ai/quiz/explain?index=0", headers=h)
        assert early.status_code == 422
        await client.post(
            "/api/v1/ai/quiz/answer",
            headers=h,
            json={"index": 0, "answer_index": 0, "kind": "quiz"},
        )
        explained = await client.get("/api/v1/ai/quiz/explain?index=0", headers=h)
        assert explained.status_code == 200
        assert explained.json()["source"] == "llm"
        again = await client.get("/api/v1/ai/quiz/explain?index=0", headers=h)
        assert again.json()["source"] == "cache"
        assert len(llm.calls) == 1
