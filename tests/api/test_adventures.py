"""A story survives reload, prevents duplicate moves, and earns a task reward."""

from uuid import uuid4

from httpx import AsyncClient


async def test_adventure_resume_and_claim(client: AsyncClient) -> None:
    login = await client.post("/api/v1/auth/device", json={"device_id": f"story-{uuid4()}"})
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    created = await client.post(
        "/api/v1/pet",
        headers=headers,
        json={"name": "Финик", "species": "FINIK", "weekly_income": 40},
    )
    assert created.status_code == 201

    url = "/api/v1/adventures/adventure_market"
    start = (await client.get(url, headers=headers)).json()
    assert start["stage"] == 0 and start["scene"]["kind"] == "BUDGET"
    assert start["wallet"] == 30

    actions = [
        {"expected_stage": 0, "food": 6, "water": 4, "reserve": 6},
        {"expected_stage": 1, "choice_id": "pause"},
        {"expected_stage": 2, "choice_id": "reserve"},
        {"expected_stage": 3, "choice_id": "report"},
        {"expected_stage": 4, "amount": 8},
    ]
    first = await client.post(f"{url}/play", headers=headers, json=actions[0])
    assert first.status_code == 200, first.text
    assert first.json()["stage"] == 1
    assert first.json()["pet_reaction"]
    resumed = (await client.get(url, headers=headers)).json()
    assert first.json()["pet_reaction"] == resumed["pet_reaction"]
    assert (await client.get(url, headers=headers)).json()["wallet"] == 14
    duplicate = await client.post(f"{url}/play", headers=headers, json=actions[0])
    assert duplicate.status_code == 200
    assert duplicate.json()["wallet"] == 14
    for action in actions[1:]:
        result = await client.post(f"{url}/play", headers=headers, json=action)
        assert result.status_code == 200, result.text
    final = result.json()
    assert final["completed"] is True
    assert final["medal"] == "Хранитель мечты"
    assert final["dream"] == 8

    task = next(
        item
        for item in (await client.get("/api/v1/tasks", headers=headers)).json()
        if item["slug"] == "adventure_market"
    )
    assert task["activity"] == "ADVENTURE"
    assert task["progress"] == 5 and task["done"] is True
    claim = await client.post("/api/v1/tasks/adventure_market/claim", headers=headers)
    assert claim.status_code == 200, claim.text
    assert (
        await client.post("/api/v1/tasks/adventure_market/claim", headers=headers)
    ).status_code == 422

    replay = await client.post(f"{url}/restart", headers=headers)
    assert replay.status_code == 200, replay.text
    assert replay.json()["stage"] == 0
    assert replay.json()["rewarded"] is True
    assert replay.json()["wallet"] == 30
    changed = await client.post(
        f"{url}/play",
        headers=headers,
        json={"expected_stage": 0, "food": 0, "water": 0, "reserve": 0},
    )
    assert changed.status_code == 200
    assert changed.json()["scene"]["story"].startswith("Финик ждёт помощи")
    replay_task = next(
        item
        for item in (await client.get("/api/v1/tasks", headers=headers)).json()
        if item["slug"] == "adventure_market"
    )
    assert replay_task["done"] is True and replay_task["rewarded"] is True
