"""Money and real-calendar invariants of the Android integration contract."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from application.use_cases import calendar


async def login(client, *, mode="normal", preset=None, device=None, timezone="Europe/Moscow"):
    body = {"device_id": device or str(uuid4()), "timezone": timezone, "mode": mode}
    if preset:
        body["demo_preset"] = preset
    response = await client.post("/api/v1/auth/device", json=body)
    assert response.status_code == 200, response.text
    token = response.json()
    return {"Authorization": f"Bearer {token['token']}"}, token


async def create(client, headers, income=40):
    response = await client.post(
        "/api/v1/pet",
        headers=headers,
        json={
            "name": "Сова",
            "species": "OWL",
            "weekly_income": income,
            "look_variant": 5,
            "accessories": ["hat", "bandana"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def state(client, headers):
    response = await client.get("/api/v1/state", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def entries(body):
    return {row["category"]: row for row in body["week"]["entries"]}


async def plan(client, headers, **values):
    totals = {"food": 0, "water": 0, "play": 0, "save": 0, **values}
    response = await client.put("/api/v1/plan", headers=headers, json=totals)
    assert response.status_code == 200, response.text
    response = await client.post("/api/v1/plan/confirm", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_empty_first_plan_partial_confirmation_topup_and_money_conservation(client):
    headers, _ = await login(client)
    initial = await create(client, headers)
    assert initial["free_coins"] == 40
    assert len(initial["goals"]) == 3
    assert initial["pet"]["species"] == "OWL"
    assert initial["pet"]["look_variant"] == 5
    assert set(initial["pet"]["accessories"]) == {"hat", "bandana"}
    assert all(e["planned"] == 0 for e in initial["week"]["entries"])
    result = await plan(client, headers, food=3, save=10)
    assert result["free_coins"] == 27
    response = await client.post("/api/v1/care", headers=headers, json={"category": "FOOD"})
    assert response.status_code == 200, response.text
    assert response.json()["xp_gained"] == 1
    assert response.json()["restored"] == 22
    response = await client.put(
        "/api/v1/plan", headers=headers, json={"food": 6, "water": 0, "play": 0, "save": 10}
    )
    assert response.status_code == 200, response.text
    assert response.json()["free_coins"] == 24  # Spent coins must not be subtracted twice.
    transfer = await client.put(
        "/api/v1/plan", headers=headers, json={"food": 5, "water": 1, "play": 0, "save": 10}
    )
    assert transfer.status_code == 422
    topup = await client.post("/api/v1/plan/topup", headers=headers, json={"water": 2})
    assert topup.status_code == 200
    assert topup.json()["free_coins"] == 22


async def test_multiple_goal_balances_save_deposit_play_withdrawal(client):
    headers, _ = await login(client)
    await create(client, headers)
    await plan(client, headers, save=15)
    response = await client.post("/api/v1/goal/deposit", headers=headers, json={"amount": 10})
    body = response.json()
    assert response.status_code == 200, response.text
    assert body["free_coins"] == 25 and body["goal"]["saved"] == 10
    assert entries(body)["SAVE"]["left"] == 5
    response = await client.put("/api/v1/goal", headers=headers, json={"slug": "watering_kit"})
    assert response.json()["goal"]["saved"] == 0
    await client.post("/api/v1/goal/deposit", headers=headers, json={"amount": 5})
    await client.put("/api/v1/goal", headers=headers, json={"slug": "sunny_window"})
    response = await client.post("/api/v1/goal/withdraw", headers=headers, json={"amount": 4})
    assert response.json()["goal"]["saved"] == 6
    assert entries(response.json())["PLAY"]["left"] == 4
    assert response.json()["free_coins"] == 25
    assert {g["catalog_slug"]: g["saved"] for g in response.json()["goals"]} == {
        "sunny_window": 6,
        "watering_kit": 5,
        "play_garden": 0,
    }


async def test_normal_clock_cannot_be_skipped_and_timezone_cannot_regrant_income(
    client, monkeypatch
):
    now = datetime(2026, 9, 27, 20, 59, tzinfo=UTC)  # Sunday 23:59 Moscow
    monkeypatch.setattr(calendar, "now_utc", lambda: now)
    device = str(uuid4())
    headers, _ = await login(client, device=device)
    initial = await create(client, headers)
    assert initial["week"]["day"] == 7
    for endpoint in ("/day/end", "/demo/advance"):
        response = await client.post("/api/v1" + endpoint, headers=headers, json={"days": 7})
        assert response.status_code == 403
    now = datetime(2026, 9, 27, 21, 0, tzinfo=UTC)
    result = await state(client, headers)
    assert result["week"]["number"] == 2
    assert result["week"]["day"] == 1
    assert result["free_coins"] == 80
    assert (await state(client, headers))["free_coins"] == 80
    headers, token = await login(client, device=device, timezone="America/Los_Angeles")
    assert token["timezone"] == "Europe/Moscow"
    assert (await state(client, headers))["free_coins"] == 80


async def test_missed_weeks_receive_only_current_income_and_seven_day_bonuses(client, monkeypatch):
    now = datetime(2026, 9, 7, 9, tzinfo=UTC)
    monkeypatch.setattr(calendar, "now_utc", lambda: now)
    headers, _ = await login(client)
    await create(client, headers)
    now = datetime(2026, 9, 28, 9, tzinfo=UTC)
    bodies = await asyncio.gather(*(state(client, headers) for _ in range(3)))
    assert {body["free_coins"] for body in bodies} == {95}  # 40 + current40 + 3*5
    assert {body["week"]["number"] for body in bodies} == {4}
    assert all(n["percent"] == 0 for n in bodies[0]["pet"]["needs"])


async def test_carryovers_interest_and_task_rewards_at_close(client, monkeypatch):
    monkeypatch.setattr(calendar, "now_utc", lambda: datetime(2026, 9, 27, 12, tzinfo=UTC))
    headers, _ = await login(client, mode="demo")
    await create(client, headers, income=60)
    await plan(client, headers, food=10, save=40)
    result = await client.post("/api/v1/demo/advance", headers=headers, json={"to_week_end": True})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["goal"]["saved"] == 42
    assert body["week"]["number"] == 2
    assert body["free_coins"] >= 80  # free10 + returned10 + income60 + completed rewards
    same = await state(client, headers)
    assert same["goal"]["saved"] == 42 and same["free_coins"] == body["free_coins"]


@pytest.mark.parametrize(
    "instant", [datetime(2026, 3, 7, 17, tzinfo=UTC), datetime(2026, 10, 31, 16, tzinfo=UTC)]
)
async def test_demo_advances_local_days_across_dst_once(client, monkeypatch, instant):
    monkeypatch.setattr(calendar, "now_utc", lambda: instant)
    headers, _ = await login(client, mode="demo", timezone="America/New_York")
    initial = await create(client, headers)
    response = await client.post("/api/v1/demo/advance", headers=headers, json={"days": 1})
    assert response.status_code == 200, response.text
    body = response.json()
    diff = datetime.fromisoformat(body["game_now"]) - datetime.fromisoformat(initial["game_now"])
    assert diff.total_seconds() in (23 * 3600, 25 * 3600)
    assert {n["category"]: n["percent"] for n in body["pet"]["needs"]} == {
        "FOOD": 58,
        "WATER": 55,
        "PLAY": 52,
    }
    assert (await state(client, headers))["pet"]["needs"] == body["pet"]["needs"]


async def test_demo_isolated_and_explicit_preset_resets_only_demo(client):
    device = str(uuid4())
    normal, _ = await login(client, device=device)
    await create(client, normal)
    demo, token = await login(client, device=device, mode="demo", preset="prepared")
    assert token["has_pet"] is True
    body = await state(client, demo)
    assert body["pet"]["xp"] == 160 and body["goal"]["saved"] == 35
    resumed, token = await login(client, device=device, mode="demo")
    assert token["has_pet"] is True
    assert (await state(client, resumed))["pet"]["xp"] == 160
    _, token = await login(client, device=device, mode="demo", preset="new")
    assert token["has_pet"] is False
    assert (await state(client, normal))["pet"]["xp"] == 0


async def test_concurrent_deposits_cannot_spend_same_money_twice(client):
    headers, _ = await login(client)
    await create(client, headers)
    await plan(client, headers, save=10)
    results = await asyncio.gather(
        *(
            client.post("/api/v1/goal/deposit", headers=headers, json={"amount": 10})
            for _ in range(2)
        )
    )
    assert sorted(response.status_code for response in results) == [200, 422]
    assert (await state(client, headers))["goal"]["saved"] == 10


async def test_profile_totals_include_bonus_and_net_all_goal_savings(client):
    headers, _ = await login(client)
    await create(client, headers)
    await plan(client, headers, save=10)
    bonus = await client.post(
        "/api/v1/parent/bonus",
        headers=headers,
        json={"amount": 5, "reason": "Помощь", "pin": "1234"},
    )
    assert bonus.status_code == 200
    await client.post("/api/v1/goal/deposit", headers=headers, json={"amount": 10})
    profile = (await client.get("/api/v1/profile", headers=headers)).json()
    assert profile["earned_total"] == 45
    assert profile["saved_total"] == 10
    await client.post("/api/v1/goal/withdraw", headers=headers, json={"amount": 4})
    profile = (await client.get("/api/v1/profile", headers=headers)).json()
    assert profile["earned_total"] == 45 and profile["saved_total"] == 6


async def test_daily_zero_needs_can_roll_back_owl_stage(client):
    headers, _ = await login(client, mode="demo", preset="prepared")
    initial = await state(client, headers)
    result = await client.post("/api/v1/demo/advance", headers=headers, json={"days": 7})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["pet"]["xp"] < initial["pet"]["xp"]
    assert body["pet"]["stage_index"] < initial["pet"]["stage_index"]
    assert body["streak"]["count"] == 0
