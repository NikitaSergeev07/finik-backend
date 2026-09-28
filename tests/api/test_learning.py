"""Повторение появляется после ошибки и проверяется на сервере."""

from datetime import timedelta
from uuid import uuid4

from httpx import AsyncClient

from application.use_cases import learning


async def test_review_after_mistake(client: AsyncClient, monkeypatch) -> None:
    login = await client.post("/api/v1/auth/device", json={"device_id": f"learn-{uuid4()}"})
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    created = await client.post(
        "/api/v1/pet", headers=headers,
        json={"name": "Финик", "species": "FINIK", "weekly_income": 40},
    )
    assert created.status_code == 201
    first = (await client.get("/api/v1/tasks/lesson_discount/questions", headers=headers)).json()[0]
    wrong = await client.post(
        "/api/v1/tasks/lesson_discount/answer", headers=headers,
        json={"question_slug": first["slug"], "answer_index": 0},
    )
    assert wrong.status_code == 200 and wrong.json()["correct"] is False

    today = learning._today()
    upcoming = (await client.get("/api/v1/learning/review", headers=headers)).json()
    assert upcoming["topic"] is None
    assert upcoming["next_due"] == (today + timedelta(days=1)).isoformat()

    monkeypatch.setattr(learning, "_today", lambda: today + timedelta(days=1))
    due = (await client.get("/api/v1/learning/review", headers=headers)).json()
    assert due["topic"] == "lesson_discount"
    assert len(due["options"]) == 3
    assert "right_index" not in due
    index = int(due["question"].split("стоила ")[1].split(" ")[0])
    saving = int(due["question"].split("равна ")[1].split(" ")[0])
    right = due["options"].index(str(index - saving))
    wrong_index = (right + 1) % 3

    incorrect = await client.post(
        "/api/v1/learning/review/answer", headers=headers,
        json={"topic": due["topic"], "answer_index": wrong_index},
    )
    assert incorrect.status_code == 200 and incorrect.json()["correct"] is False
    assert str(index - saving) not in incorrect.json()["explanation"]
    correct = await client.post(
        "/api/v1/learning/review/answer", headers=headers,
        json={"topic": due["topic"], "answer_index": right},
    )
    assert correct.status_code == 200 and correct.json()["correct"] is True
    assert (await client.get("/api/v1/learning/review", headers=headers)).json()["topic"] is None
    duplicate = await client.post(
        "/api/v1/learning/review/answer", headers=headers,
        json={"topic": due["topic"], "answer_index": right},
    )
    assert duplicate.status_code == 422
