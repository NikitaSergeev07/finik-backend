"""Agreed mobile/server money flows and normal/demo isolation over the public API."""

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from httpx import AsyncClient


async def login(
    client: AsyncClient,
    *,
    device: str | None = None,
    mode: str = "normal",
    preset: str | None = None,
    timezone: str = "Europe/Moscow",
) -> tuple[str, dict[str, str], dict]:
    device = device or f"contract-{uuid4()}"
    body = {"device_id": device, "mode": mode, "timezone": timezone}
    if preset is not None:
        body["demo_preset"] = preset
    response = await client.post("/api/v1/auth/device", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    return device, {"Authorization": f"Bearer {data['token']}"}, data


async def create_owl(client: AsyncClient, headers: dict[str, str]) -> dict:
    response = await client.post(
        "/api/v1/pet",
        headers=headers,
        json={
            "name": "Совушка",
            "species": "OWL",
            "weekly_income": 40,
            "goal_slug": "sunny_window",
            "look_variant": 5,
            "accessories": ["hat", "backpack"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def entries(state: dict) -> dict[str, dict]:
    return {entry["category"]: entry for entry in state["week"]["entries"]}


async def test_mobile_money_flow_is_server_authoritative(client: AsyncClient) -> None:
    device, headers, token = await login(client)
    assert not token["has_pet"]
    state = await create_owl(client, headers)
    assert state["free_coins"] == 40
    assert all(entry["planned"] == 0 for entry in entries(state).values())
    assert state["pet"]["species"] == "OWL"
    assert state["pet"]["look_variant"] == 5
    assert set(state["pet"]["accessories"]) == {"hat", "backpack"}

    response = await client.put(
        "/api/v1/plan",
        headers=headers,
        json={"food": 10, "water": 8, "play": 4, "save": 10},
    )
    assert response.status_code == 200, response.text
    assert response.json()["free_coins"] == 8
    response = await client.post("/api/v1/plan/confirm", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["week"]["plan_confirmed"]

    response = await client.post("/api/v1/goal/deposit", headers=headers, json={"amount": 6})
    assert response.status_code == 200, response.text
    state = response.json()
    assert state["goal"]["saved"] == 6
    assert state["free_coins"] == 8
    assert entries(state)["SAVE"]["left"] == 4

    response = await client.put(
        "/api/v1/plan",
        headers=headers,
        json={"food": 12, "water": 8, "play": 4, "save": 10},
    )
    assert response.status_code == 200, response.text
    assert response.json()["free_coins"] == 6
    response = await client.put(
        "/api/v1/plan",
        headers=headers,
        json={"food": 11, "water": 9, "play": 4, "save": 10},
    )
    assert response.status_code == 422, response.text

    response = await client.post("/api/v1/goal/withdraw", headers=headers, json={"amount": 2})
    assert response.status_code == 200, response.text
    state = response.json()
    assert state["goal"]["saved"] == 4
    assert state["free_coins"] == 6
    assert entries(state)["PLAY"]["left"] == 6

    response = await client.put("/api/v1/goal", headers=headers, json={"slug": "watering_kit"})
    assert response.status_code == 200, response.text
    assert response.json()["goal"]["saved"] == 0
    response = await client.post("/api/v1/goal/deposit", headers=headers, json={"amount": 2})
    assert response.status_code == 200, response.text
    state = response.json()
    balances = {goal["catalog_slug"]: goal["saved"] for goal in state["goals"]}
    assert balances["sunny_window"] == 4
    assert balances["watering_kit"] == 2
    assert entries(state)["SAVE"]["left"] == 2

    _, restored_headers, token = await login(client, device=device)
    assert token["has_pet"]
    restored = await client.get("/api/v1/state", headers=restored_headers)
    assert restored.status_code == 200, restored.text
    assert restored.json()["free_coins"] == state["free_coins"]
    assert restored.json()["goals"] == state["goals"]


async def test_normal_clock_uses_local_calendar_and_cannot_be_skipped(client: AsyncClient) -> None:
    _, headers, _ = await login(client, timezone="America/New_York")
    state = await create_owl(client, headers)
    assert state["timezone"] == "America/New_York"
    assert state["mode"] == "normal"
    assert not state["can_advance_time"]
    zone = ZoneInfo(state["timezone"])
    start = datetime.fromisoformat(state["week"]["starts_at"]).astimezone(zone)
    end = datetime.fromisoformat(state["week"]["ends_at"]).astimezone(zone)
    assert start.weekday() == end.weekday() == 0
    assert start.hour == start.minute == end.hour == end.minute == 0
    assert (end.date() - start.date()).days == 7
    for route, body in (("/day/end", None), ("/demo/advance", {"days": 7})):
        response = await client.post(f"/api/v1{route}", headers=headers, json=body)
        assert response.status_code == 403, response.text
    after = (await client.get("/api/v1/state", headers=headers)).json()
    assert after["week"]["id"] == state["week"]["id"]
    assert after["free_coins"] == 40


async def test_demo_scenarios_are_fresh_and_isolated_from_normal(client: AsyncClient) -> None:
    device, normal_headers, _ = await login(client)
    normal = await create_owl(client, normal_headers)
    _, demo_headers, token = await login(client, device=device, mode="demo", preset="prepared")
    assert token["has_pet"]
    demo_response = await client.get("/api/v1/state", headers=demo_headers)
    assert demo_response.status_code == 200, demo_response.text
    demo = demo_response.json()
    assert demo["mode"] == "demo" and demo["can_advance_time"]
    assert demo["pet"]["id"] != normal["pet"]["id"]
    response = await client.post("/api/v1/demo/advance", headers=demo_headers, json={"days": 1})
    assert response.status_code == 200, response.text
    advanced = response.json().get("state", response.json())
    assert datetime.fromisoformat(advanced["game_now"]) > datetime.fromisoformat(demo["game_now"])

    unchanged = (await client.get("/api/v1/state", headers=normal_headers)).json()
    assert unchanged["pet"]["id"] == normal["pet"]["id"]
    assert unchanged["free_coins"] == normal["free_coins"]
    assert unchanged["week"]["id"] == normal["week"]["id"]

    _, fresh_headers, token = await login(client, device=device, mode="demo", preset="new")
    assert not token["has_pet"]
    response = await client.get("/api/v1/state", headers=fresh_headers)
    assert response.status_code == 404, response.text
    _, restored_headers, normal_token = await login(client, device=device)
    assert normal_token["has_pet"]
    restored = (await client.get("/api/v1/state", headers=restored_headers)).json()
    assert restored["pet"]["id"] == normal["pet"]["id"]
