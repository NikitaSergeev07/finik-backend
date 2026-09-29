"""Обязательный минимум ТЗ: цели, план, словарь, лавка, задания."""

from uuid import uuid4

from httpx import AsyncClient


async def login(client: AsyncClient) -> dict[str, str]:
    r = await client.post("/api/v1/auth/device", json={"device_id": f"test-{uuid4()}"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def start(client: AsyncClient, **pet: object) -> dict[str, str]:
    h = await login(client)
    body = {"name": "Кустик", "species": "CACTUS", "weekly_income": 40, **pet}
    r = await client.post("/api/v1/pet", headers=h, json=body)
    assert r.status_code == 201, r.text
    return h


async def test_goal_catalog_and_select(client: AsyncClient):
    h = await login(client)
    r = await client.get("/api/v1/content/goals", headers=h)
    assert r.status_code == 200
    goals = r.json()
    assert len(goals) >= 3
    slugs = {g["slug"] for g in goals}
    assert {"sunny_window", "watering_kit", "play_garden"} <= slugs
    assert all(g["title"] and g["target"] > 0 and g["why"] for g in goals)

    r = await client.post(
        "/api/v1/pet",
        headers=h,
        json={
            "name": "Кустик",
            "species": "FINIK",
            "weekly_income": 40,
            "goal_slug": "watering_kit",
            "look_variant": 2,
        },
    )
    assert r.status_code == 201, r.text
    state = r.json()
    assert state["goal"]["title"] == "Набор для заботы"
    assert state["goal"]["target"] == 80
    assert state["goal"]["catalog_slug"] == "watering_kit"
    assert state["goal"]["remain"] == 80
    assert state["pet"]["look_variant"] == 2
    assert state["last_income"] == 40
    assert "доход" in state["last_income_note"].lower()

    r = await client.put("/api/v1/goal", headers=h, json={"slug": "play_garden"})
    assert r.status_code == 200
    assert r.json()["goal"]["catalog_slug"] == "play_garden"
    assert r.json()["goal"]["target"] == 120

    r = await client.put("/api/v1/goal", headers=h, json={"slug": "nope"})
    assert r.status_code == 422


async def test_plan_confirm_locks(client: AsyncClient):
    h = await start(client)
    r = await client.get("/api/v1/state", headers=h)
    assert r.json()["week"]["plan_confirmed"] is False

    r = await client.put(
        "/api/v1/plan", headers=h, json={"food": 14, "water": 4, "play": 6, "save": 16}
    )
    assert r.status_code == 200

    r = await client.post("/api/v1/plan/confirm", headers=h)
    assert r.status_code == 200 and r.json()["week"]["plan_confirmed"] is True
    assert r.json()["free_coins"] == 0

    r = await client.put(
        "/api/v1/plan", headers=h, json={"food": 10, "water": 10, "play": 10, "save": 10}
    )
    assert r.status_code == 422
    r = await client.post("/api/v1/plan/confirm", headers=h)
    assert r.status_code == 422


async def test_terms_glossary(client: AsyncClient):
    h = await start(client)
    r = await client.get("/api/v1/content/terms", headers=h)
    assert r.status_code == 200
    words = {t["word"] for t in r.json()}
    assert {"Бюджет", "Копилка", "Скидка", "Перерасход"} <= words
    assert all(t["meaning"] and t["example"] for t in r.json())


async def test_shop_minima_and_effects(client: AsyncClient):
    h = await start(client)
    items = (await client.get("/api/v1/shop/items", headers=h)).json()
    visible = [i for i in items if i["slug"] != "berry_treat"]
    assert len(visible) >= 8
    kinds = {i["kind"] for i in visible}
    assert kinds == {"NEED", "WANT"}
    ball = next(i for i in items if i["slug"] == "ball")
    assert ball["restore"] == 25 and ball["xp_bonus"] == 0 and ball["kind"] == "WANT"
    water = next(i for i in items if i["slug"] == "water_3d")
    assert water["restore"] == 45 and water["kind"] == "NEED"


async def test_six_tasks_three_themes(client: AsyncClient):
    h = await start(client)
    tasks = (await client.get("/api/v1/tasks", headers=h)).json()
    slugs = {t["slug"] for t in tasks}
    assert len(tasks) >= 6
    assert {
        "food_plan",
        "save_10",
        "buy_sale",
        "buy_need",
        "lesson_discount",
        "lesson_need_want",
    } <= slugs
