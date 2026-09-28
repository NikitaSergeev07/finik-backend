"""Лавка, задания с уроком и история недель."""

from uuid import uuid4

from httpx import AsyncClient


async def start(client: AsyncClient) -> dict[str, str]:
    r = await client.post("/api/v1/auth/device", json={"device_id": f"test-{uuid4()}"})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    r = await client.post(
        "/api/v1/pet", headers=h, json={"name": "Кустик", "species": "CACTUS", "weekly_income": 40}
    )
    assert r.status_code == 201
    return h


async def test_shop_buy_and_discount_task(client: AsyncClient):
    h = await start(client)
    r = await client.get("/api/v1/shop/items", headers=h)
    assert r.status_code == 200
    items = {i["slug"]: i for i in r.json()}
    assert items["ball"]["sale_percent"] == 40 and items["ball"]["affordable"]
    assert items["new_pot"]["affordable"] is False  # в играх 4, горшок стоит 18

    r = await client.post("/api/v1/shop/buy", headers=h, json={"slug": "new_pot"})
    assert r.status_code == 422

    r = await client.post("/api/v1/shop/buy", headers=h, json={"slug": "ball"})
    assert r.status_code == 200, r.text
    assert r.json()["restored"] == 25
    play = next(e for e in r.json()["state"]["week"]["entries"] if e["category"] == "PLAY")
    assert play["spent"] == 3

    r = await client.get("/api/v1/tasks", headers=h)
    tasks = {t["slug"]: t for t in r.json()}
    assert tasks["buy_sale"]["done"] is True and tasks["buy_sale"]["rewarded"] is False
    assert tasks["streak_7"]["progress"] == 0

    r = await client.post("/api/v1/tasks/buy_sale/claim", headers=h)
    assert r.status_code == 200 and r.json()["free_coins"] == 4
    r = await client.post("/api/v1/tasks/buy_sale/claim", headers=h)
    assert r.status_code == 422
    r = await client.post("/api/v1/tasks/streak_7/claim", headers=h)
    assert r.status_code == 422


async def test_lesson_quiz(client: AsyncClient):
    h = await start(client)
    r = await client.get("/api/v1/tasks/lesson_discount/questions", headers=h)
    qs = r.json()
    assert len(qs) == 3 and "right_index" not in qs[0]

    r = await client.post(
        "/api/v1/tasks/lesson_discount/answer",
        headers=h,
        json={"question_slug": qs[0]["slug"], "answer_index": 0},
    )
    assert r.json()["correct"] is False and "4" in r.json()["explanation"]
    r = await client.post(
        "/api/v1/tasks/lesson_discount/answer",
        headers=h,
        json={"question_slug": qs[0]["slug"], "answer_index": 1},
    )
    assert r.status_code == 422  # повторно нельзя

    for q, right in zip(qs[1:], (1, 0), strict=True):
        r = await client.post(
            "/api/v1/tasks/lesson_discount/answer",
            headers=h,
            json={"question_slug": q["slug"], "answer_index": right},
        )
        assert r.json()["correct"] is True
    assert r.json()["lesson_done"] is False  # первый вопрос отвечен неверно

    r = await client.get("/api/v1/tasks", headers=h)
    lesson = next(t for t in r.json() if t["slug"] == "lesson_discount")
    assert lesson["progress"] == 2 and lesson["goal"] == 3


async def test_history_after_week(client: AsyncClient):
    h = await start(client)
    r = await client.get("/api/v1/weeks/history", headers=h)
    assert r.json()["weeks"] == []
    await client.post("/api/v1/care", headers=h, json={"category": "FOOD"})
    for _ in range(7):
        await client.post("/api/v1/day/end", headers=h)
    r = await client.get("/api/v1/weeks/history", headers=h)
    body = r.json()
    assert len(body["weeks"]) == 1 and body["weeks"][0]["saved"] == 8
    assert body["weeks"][0]["tone"] == "HIGH"
    food = next(row for row in body["last_report"] if row["category"] == "FOOD")
    assert food["actual"] == 3 and food["is_over"] is False
    assert body["last_summary"].startswith("План 40")


async def test_hidden_item_absent_until_unlock(client: AsyncClient):
    h = await start(client)
    slugs = {i["slug"] for i in (await client.get("/api/v1/shop/items", headers=h)).json()}
    assert "berry_treat" not in slugs
    assert "ball" in slugs
