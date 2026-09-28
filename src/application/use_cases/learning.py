"""Память навыков, повторение и подсказки по ошибкам."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from application import ai_prompts
from application.ports import LlmGateway, UnitOfWork
from application.use_cases._common import load_state
from core.errors import NotFound, RuleViolation
from domain.services import learning as learning_rules
from domain.services import persona, safety


@dataclass(frozen=True, slots=True)
class HintView:
    text: str
    source: str


@dataclass(frozen=True, slots=True)
class ReviewView:
    topic: str | None
    title: str
    question: str
    options: tuple[str, ...]
    next_due: date | None


@dataclass(frozen=True, slots=True)
class ReviewAnswerView:
    correct: bool
    explanation: str
    next_due: date | None


def _today() -> date:
    return datetime.now(ZoneInfo("Europe/Moscow")).date()


def _progress_key(player_id: UUID) -> str:
    return f"learning-v1:{player_id}"


async def _read_progress(uow: UnitOfWork, player_id: UUID) -> dict[str, dict[str, object]]:
    raw = await uow.ai.get(_progress_key(player_id))
    return json.loads(raw) if raw else {}


async def _write_progress(
    uow: UnitOfWork, player_id: UUID, progress: dict[str, dict[str, object]]
) -> None:
    await uow.ai.put(
        _progress_key(player_id),
        json.dumps(progress, ensure_ascii=False),
        player_id=player_id,
        kind="learning-progress",
    )


def _update_topic(row: dict[str, object], correct: bool, today: date, *, review: bool) -> None:
    row["attempts"] = int(row.get("attempts", 0)) + 1
    if not correct:
        row["streak"] = 0
        row["missed_on"] = today.isoformat()
        due = today if review else learning_rules.next_due(0, today, missed=True)
        row["due"] = due.isoformat()
        return
    row["correct"] = int(row.get("correct", 0)) + 1
    if row.get("missed_on") == today.isoformat():
        row["streak"] = 0
        row["due"] = learning_rules.next_due(0, today, missed=True).isoformat()
    elif row.get("last_success") != today.isoformat():
        streak = int(row.get("streak", 0)) + 1
        row["streak"] = streak
        row["due"] = learning_rules.next_due(streak, today).isoformat()
    row["last_success"] = today.isoformat()


async def record_attempt(
    uow: UnitOfWork, player_id: UUID, topic: str, correct: bool, *, review: bool = False
) -> None:
    if topic not in learning_rules.TOPIC_TITLES:
        return
    progress = await _read_progress(uow, player_id)
    row = progress.setdefault(topic, {})
    _update_topic(row, correct, _today(), review=review)
    await _write_progress(uow, player_id, progress)


def _due_topic(progress: dict[str, dict[str, object]], today: date) -> str | None:
    due = [
        (str(row["due"]), int(row.get("correct", 0)), topic)
        for topic, row in progress.items()
        if topic in learning_rules.TOPIC_TITLES
        and str(row.get("due", "9999-12-31")) <= today.isoformat()
    ]
    return min(due)[2] if due else None


async def review(uow: UnitOfWork, player_id: UUID) -> ReviewView:
    today = _today()
    async with uow:
        await load_state(uow, player_id)
        progress = await _read_progress(uow, player_id)
        topic = _due_topic(progress, today)
        if topic:
            question = learning_rules.review_question(topic, str(player_id), today)
            return ReviewView(topic, question.title, question.question, question.options, today)
        dates = [
            date.fromisoformat(str(row["due"]))
            for topic, row in progress.items()
            if topic in learning_rules.TOPIC_TITLES and row.get("due")
        ]
        return ReviewView(None, "Повторение", "", (), min(dates) if dates else None)


async def answer_review(
    uow: UnitOfWork, player_id: UUID, topic: str, answer_index: int
) -> ReviewAnswerView:
    today = _today()
    async with uow:
        await load_state(uow, player_id)
        progress = await _read_progress(uow, player_id)
        if topic != _due_topic(progress, today):
            raise RuleViolation("Открой сегодняшнее повторение заново")
        question = learning_rules.review_question(topic, str(player_id), today)
        if answer_index < 0 or answer_index >= len(question.options):
            raise RuleViolation("Выбери ответ")
        correct = answer_index == question.right_index
        row = progress[topic]
        _update_topic(row, correct, today, review=True)
        await _write_progress(uow, player_id, progress)
        await uow.commit()
        explanation = question.explanation if correct else "Проверь расчёт и попробуй ещё раз."
        next_date = date.fromisoformat(str(row["due"])) if correct else today
        return ReviewAnswerView(correct, explanation, next_date)


async def hint(
    uow: UnitOfWork, llm: LlmGateway, player_id: UUID, lesson_slug: str, question_slug: str
) -> HintView:
    async with uow:
        state = await load_state(uow, player_id)
        progress = await uow.tasks.get_progress(player_id, state.week.id, lesson_slug)
        mistake = progress.data.get("last_mistake") if progress else None
        if not isinstance(mistake, dict) or mistake.get("question_slug") != question_slug:
            raise RuleViolation("Сначала попробуй ответить на вопрос")
        questions = await uow.tasks.list_questions(lesson_slug)
        question = next((q for q in questions if q.slug == question_slug), None)
        if question is None:
            raise NotFound("Вопрос не найден")
        selected = str(mistake.get("selected", ""))
        wrong_answer = (
            question.options[int(selected)]
            if selected.isdigit()
            and question.activity != "COINS"
            and int(selected) < len(question.options)
            else selected
        )
        correct_answer = question.options[question.right_index]
        species = state.pet.species
        fallback = persona.VOICE_OPENING[species] + _hint_fallback(lesson_slug)
        key_data = f"{player_id}:{species.value}:{question_slug}:{selected}"
        key = "lesson-hint-v1:" + hashlib.sha256(key_data.encode()).hexdigest()[:36]
        cached = await uow.ai.get(key) if llm.enabled else None
        system, user = ai_prompts.lesson_hint(
            state.pet.name, species, question.question, wrong_answer, question.explanation
        )
    if cached:
        return HintView(cached, "cache")
    if not llm.enabled:
        return HintView(fallback, "fallback")
    raw = await llm.complete(system=system, user=user, max_tokens=100, temperature=0.5)
    text = safety.sanitize(raw or "", limit=220, sentences=2)
    answer_number = re.search(r"\d+", correct_answer)
    reveals_number = bool(
        answer_number and re.search(rf"(?<!\d){answer_number.group()}(?!\d)", text)
    )
    if (
        not text
        or safety.is_blocked(text)
        or correct_answer.lower() in text.lower()
        or reveals_number
    ):
        return HintView(fallback, "fallback")
    async with uow:
        await uow.ai.put(key, text, player_id=player_id, kind="lesson-hint")
        await uow.commit()
    return HintView(text, "llm")


def _hint_fallback(topic: str) -> str:
    if topic in {"lesson_budget", "lesson_saving", "lesson_earn", "lesson_debt"}:
        return "разложи монеты по шагам и проверь, что нужно вычесть первым?"
    if topic in {"lesson_discount", "lesson_compare"}:
        return "сравни старую и новую цену. Какая часть монет остаётся у тебя?"
    return "что питомцу необходимо сегодня, а какая покупка может подождать?"
