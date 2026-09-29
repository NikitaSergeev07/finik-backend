"""События дня, достижения, профиль и сброс."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("monday_clock")


async def start(client: AsyncClient, species: str = "FINIK") -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/device", json={"device_id": f"test-{uuid4()}", "mode": "demo"}
    )
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    await client.post(
        "/api/v1/pet", headers=h, json={"name": "Кустик", "species": species, "weekly_income": 40}
    )
    await client.put(
        "/api/v1/plan", headers=h, json={"food": 16, "water": 12, "play": 4, "save": 8}
    )
    await client.post("/api/v1/plan/confirm", headers=h)
    return h


async def test_event_is_stable_and_choice_applies_once(client: AsyncClient):
    h = await start(client)
    r1 = await client.get("/api/v1/events/today", headers=h)
    r2 = await client.get("/api/v1/events/today", headers=h)
    assert r1.status_code == 200 and r1.json()["id"] == r2.json()["id"]
    ev = r1.json()
    assert ev["chosen"] is None and len(ev["options"]) >= 1

    key = ev["options"][-1]["key"]
    r = await client.post(f"/api/v1/events/{ev['id']}/choose", headers=h, json={"option": key})
    assert r.status_code == 200, r.text
    assert "state" in r.json()
    r = await client.post(f"/api/v1/events/{ev['id']}/choose", headers=h, json={"option": key})
    assert r.status_code == 422

    r = await client.get("/api/v1/events/today", headers=h)
    assert r.json()["chosen"] == key

    await client.post("/api/v1/day/end", headers=h)
    r = await client.get("/api/v1/events/today", headers=h)
    assert r.json()["id"] != ev["id"] and r.json()["day"] == 2


async def test_scam_needs_free_coins(client: AsyncClient):
    """Без свободных монет мошеннику нечего переводить: правило не даёт уйти в минус."""
    h = await start(client)
    # Перебираем дни, пока не встретим мошенника: выбор детерминирован, но зависит от игрока.
    for _ in range(40):
        ev = (await client.get("/api/v1/events/today", headers=h)).json()
        if ev and ev["slug"] == "scam_message":
            free = (await client.get("/api/v1/state", headers=h)).json()["free_coins"]
            if free:  # после закрытия недели монеты есть: прячем их в мечту
                await client.post("/api/v1/plan/topup", headers=h, json={"save": free})
            r = await client.post(
                f"/api/v1/events/{ev['id']}/choose", headers=h, json={"option": "pay"}
            )
            assert r.status_code == 422  # свободных монет 0
            r = await client.post(
                f"/api/v1/events/{ev['id']}/choose", headers=h, json={"option": "ignore"}
            )
            assert r.status_code == 200 and r.json()["coins_delta"] == 2
            assert "мошен" in r.json()["note"].lower() or "обман" in r.json()["note"].lower()
            return
        await client.post("/api/v1/day/end", headers=h)


async def test_badges_and_profile(client: AsyncClient):
    h = await start(client)
    r = await client.get("/api/v1/profile/badges", headers=h)
    badges = {b["slug"]: b for b in r.json()}
    assert len(badges) == 6 and badges["no_debt"]["percent"] == 0
    for _ in range(7):
        await client.post("/api/v1/day/end", headers=h)
    r = await client.get("/api/v1/profile/badges", headers=h)
    badges = {b["slug"]: b for b in r.json()}
    assert badges["no_debt"]["is_done"] and badges["plan_kept"]["percent"] == 25
    assert badges["twenty_percent"]["percent"] == 25  # копилка 8 из 40

    r = await client.get("/api/v1/profile", headers=h)
    p = r.json()
    assert p["weeks_done"] == 1 and p["saved_total"] == 8 and p["earned_total"] >= 85

    r = await client.patch(
        "/api/v1/profile", headers=h, json={"weekly_income": 60, "sound_on": False}
    )
    assert r.status_code == 200 and r.json()["weekly_income"] == 60
    r = await client.patch("/api/v1/profile", headers=h, json={"weekly_income": 55})
    assert r.status_code == 422


async def test_reset_keeps_token(client: AsyncClient):
    h = await start(client)
    r = await client.post("/api/v1/profile/reset", headers=h)
    assert r.status_code == 204
    r = await client.get("/api/v1/state", headers=h)
    assert r.status_code == 404
    r = await client.post(
        "/api/v1/pet", headers=h, json={"name": "Снова", "species": "SPARK", "weekly_income": 20}
    )
    assert r.status_code == 201 and r.json()["pet"]["name"] == "Снова"


async def test_event_mode_and_parent_bonus(client: AsyncClient):
    h = await start(client)
    r = await client.patch("/api/v1/profile", headers=h, json={"event_mode": "escalating"})
    assert r.status_code == 200
    p = (await client.get("/api/v1/profile", headers=h)).json()
    assert p["event_mode"] == "escalating" and p["vaccinated_until"] == 0

    r = await client.post(
        "/api/v1/parent/bonus",
        headers=h,
        json={"amount": 5, "reason": "убрал игрушки", "pin": "0000"},
    )
    assert r.status_code == 422
    r = await client.post(
        "/api/v1/parent/bonus",
        headers=h,
        json={"amount": 5, "reason": "убрал игрушки", "pin": "1234"},
    )
    assert r.status_code == 200 and r.json()["amount"] == 5
    assert r.json()["state"]["free_coins"] == 5
    diary = (await client.get("/api/v1/ai/diary", headers=h)).json()
    assert diary["text"]
