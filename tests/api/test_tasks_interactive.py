"""Interactive lessons allow mistakes, retries and resuming progress."""

from uuid import uuid4

from httpx import AsyncClient


async def test_lesson_retry_resume_and_reward(client: AsyncClient) -> None:
    login = await client.post("/api/v1/auth/device", json={"device_id": f"lesson-{uuid4()}"})
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    created = await client.post(
        "/api/v1/pet",
        headers=headers,
        json={"name": "Финик", "species": "FINIK", "weekly_income": 40},
    )
    assert created.status_code == 201, created.text

    tasks = (await client.get("/api/v1/tasks", headers=headers)).json()
    lessons = [task for task in tasks if task["kind"] == "LESSON"]
    assert len(lessons) == 10

    url = "/api/v1/tasks/lesson_need_want/questions"
    questions = (await client.get(url, headers=headers)).json()
    assert len(questions) == 3
    assert questions[0]["activity"] == "SORT"
    assert questions[0]["options"] == ["Нужно", "Хочется"]
    assert "right_index" not in questions[0]

    first = questions[0]["slug"]
    wrong = await client.post(
        "/api/v1/tasks/lesson_need_want/answer",
        headers=headers,
        json={"question_slug": first, "answer_index": 1},
    )
    assert wrong.status_code == 200
    assert wrong.json()["correct"] is False
    assert wrong.json()["answered"] == 0
    assert len((await client.get(url, headers=headers)).json()) == 3

    for question in questions:
        answer = await client.post(
            "/api/v1/tasks/lesson_need_want/answer",
            headers=headers,
            json={
                "question_slug": question["slug"],
                "answer_index": {"q_need_1": 0, "q_need_2": 1, "q_need_3": 1}[question["slug"]],
            },
        )
        assert answer.status_code == 200, answer.text
        assert answer.json()["correct"] is True

    assert (await client.get(url, headers=headers)).json() == []
    lesson = next(
        task
        for task in (await client.get("/api/v1/tasks", headers=headers)).json()
        if task["slug"] == "lesson_need_want"
    )
    assert lesson["done"] is True

    claim = await client.post("/api/v1/tasks/lesson_need_want/claim", headers=headers)
    assert claim.status_code == 200, claim.text
    repeat = await client.post("/api/v1/tasks/lesson_need_want/claim", headers=headers)
    assert repeat.status_code == 422


async def test_coin_game_checks_amount_on_server(client: AsyncClient) -> None:
    login = await client.post("/api/v1/auth/device", json={"device_id": f"coins-{uuid4()}"})
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    await client.post(
        "/api/v1/pet",
        headers=headers,
        json={"name": "Финик", "species": "FINIK", "weekly_income": 40},
    )
    url = "/api/v1/tasks/lesson_budget/questions"
    question = (await client.get(url, headers=headers)).json()[0]
    assert question["activity"] == "COINS"
    assert "right_index" not in question

    answer_url = "/api/v1/tasks/lesson_budget/answer"
    wrong = await client.post(
        answer_url,
        headers=headers,
        json={"question_slug": question["slug"], "answer_value": 4},
    )
    assert wrong.status_code == 200 and wrong.json()["correct"] is False
    assert (await client.get(url, headers=headers)).json()[0]["slug"] == question["slug"]

    correct = await client.post(
        answer_url,
        headers=headers,
        json={"question_slug": question["slug"], "answer_value": 3},
    )
    assert correct.status_code == 200 and correct.json()["correct"] is True
    assert (await client.get(url, headers=headers)).json()[0]["slug"] != question["slug"]


async def test_new_financial_topics_are_playable(client: AsyncClient) -> None:
    login = await client.post("/api/v1/auth/device", json={"device_id": f"topics-{uuid4()}"})
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    created = await client.post(
        "/api/v1/pet",
        headers=headers,
        json={"name": "Финик", "species": "FINIK", "weekly_income": 40},
    )
    assert created.status_code == 201

    cases = [
        ("lesson_compare", "CHOICE", {"answer_index": 1}),
        ("lesson_earn", "COINS", {"answer_value": 9}),
        ("lesson_debt", "COINS", {"answer_value": 2}),
    ]
    for slug, activity, answer in cases:
        questions = (await client.get(f"/api/v1/tasks/{slug}/questions", headers=headers)).json()
        assert len(questions) == 3
        assert questions[0]["activity"] == activity
        assert "right_index" not in questions[0]
        result = await client.post(
            f"/api/v1/tasks/{slug}/answer",
            headers=headers,
            json={"question_slug": questions[0]["slug"], **answer},
        )
        assert result.status_code == 200, result.text
        assert result.json()["correct"] is True
        remaining = (await client.get(f"/api/v1/tasks/{slug}/questions", headers=headers)).json()
        assert len(remaining) == 2
