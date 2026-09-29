"""Сквозной путь ребёнка: вход, росток, план, уход, конец дня, закрытие недели."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("monday_clock")


async def login(client: AsyncClient) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/device", json={"device_id": f"test-{uuid4()}", "mode": "demo"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["has_pet"] is False
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def test_full_week(client: AsyncClient):
    h = await login(client)

    r = await client.get("/api/v1/state", headers=h)
    assert r.status_code == 404

    r = await client.post(
        "/api/v1/pet", headers=h, json={"name": "Кустик", "species": "FINIK", "weekly_income": 40}
    )
    assert r.status_code == 201, r.text
    state = r.json()
    assert state["free_coins"] == 40 and state["pet"]["stage_name"] == "Малыш"
    assert {e["category"]: e["planned"] for e in state["week"]["entries"]} == {
        "FOOD": 0,
        "WATER": 0,
        "PLAY": 0,
        "SAVE": 0,
    }

    r = await client.post(
        "/api/v1/pet", headers=h, json={"name": "Ещё", "species": "CACTUS", "weekly_income": 40}
    )
    assert r.status_code == 409

    r = await client.put(
        "/api/v1/plan", headers=h, json={"food": 14, "water": 4, "play": 6, "save": 16}
    )
    assert r.status_code == 200, r.text
    r = await client.put(
        "/api/v1/plan", headers=h, json={"food": 30, "water": 30, "play": 0, "save": 0}
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "rule_violation"

    await client.post("/api/v1/plan/confirm", headers=h)
    r = await client.post("/api/v1/care", headers=h, json={"category": "WATER"})
    assert r.status_code == 200, r.text
    assert r.json()["xp_gained"] == 1 and r.json()["from_savings"] is False

    r = await client.post("/api/v1/care", headers=h, json={"category": "SAVE"})
    assert r.status_code == 422

    for _day in range(1, 8):
        r = await client.post("/api/v1/day/end", headers=h)
        assert r.status_code == 200, r.text
    body = r.json()
    assert body["week_finished"]
    assert body["state"]["week"]["number"] == 2 and body["state"]["week"]["day"] == 1
    assert body["state"]["goal"]["saved"] == 16
    assert body["state"]["free_coins"] >= 40 + (14 + 4 + 6 - 2) + 5
    assert body["state"]["streak"]["count"] == 0
    assert [d["done"] for d in body["state"]["streak"]["days"]] == [
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]

    await client.post("/api/v1/plan/topup", headers=h, json={"save": 10})
    await client.post("/api/v1/plan/confirm", headers=h)
    r = await client.post("/api/v1/goal/deposit", headers=h, json={"amount": 10})
    assert r.status_code == 200 and r.json()["goal"]["saved"] == 26

    r = await client.get("/api/v1/state")
    assert r.status_code == 401


async def test_streak_fills_with_days(client: AsyncClient):
    h = await login(client)
    r = await client.post(
        "/api/v1/pet", headers=h, json={"name": "Кустик", "species": "FINIK", "weekly_income": 40}
    )
    streak = r.json()["streak"]
    assert streak["goal"] == 7 and streak["bonus"] == 5 and streak["count"] == 0
    assert streak["days"][0] == {"label": "1", "done": False}
    assert streak["days"][1]["done"] is False

    await client.post("/api/v1/day/end", headers=h)
    await client.post("/api/v1/day/end", headers=h)
    streak = (await client.get("/api/v1/state", headers=h)).json()["streak"]
    assert streak["count"] == 2
    assert [d["done"] for d in streak["days"]] == [True, True, False, False, False, False, False]
