"""Game content stays playable when questions change."""

import re
from collections import Counter
from uuid import uuid4

from application.use_cases.tasks import _solved_questions
from domain.entities import TaskProgress
from infrastructure.content.catalog import QUESTION_ACTIVITY, QUIZ_QUESTIONS, TASK_DEFS


def test_every_lesson_has_three_playable_steps() -> None:
    lessons = {
        task["slug"]
        for task in TASK_DEFS
        if task["kind"] == "LESSON" and not task["params"].get("adventure")
    }
    counts = Counter(question["lesson_slug"] for question in QUIZ_QUESTIONS)
    assert lessons == set(counts)
    assert all(counts[lesson] == 3 for lesson in lessons)
    assert {question["slug"] for question in QUIZ_QUESTIONS} == set(QUESTION_ACTIVITY)

    for question in QUIZ_QUESTIONS:
        options = question["options"]
        assert 0 <= question["right_index"] < len(options)
        activity, scene = QUESTION_ACTIVITY[question["slug"]]
        assert activity in {"COINS", "SORT", "CHOICE"}
        assert scene
        if activity == "COINS":
            assert all(re.search(r"\d+", option) for option in options)
        if activity == "SORT":
            assert len(options) == 2


def test_old_wrong_answer_progress_can_restart() -> None:
    progress = TaskProgress(
        player_id=uuid4(),
        week_id=uuid4(),
        task_slug="lesson_discount",
        progress=1,
        data={"answered": ["q_discount_1", "q_discount_2"]},
    )
    solved, reset = _solved_questions(progress)
    assert reset is True
    assert solved == []
    assert progress.progress == 0
    assert progress.data["answered"] == []
