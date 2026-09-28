"""Задания недели: список с прогрессом, ответ на вопрос урока, получение награды."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases import learning
from application.use_cases._common import load_state
from core.errors import NotFound, RuleViolation
from domain.entities import LogEntry, QuizQuestion, TaskDef, TaskProgress
from domain.enums import ActionKind, TaskKind
from domain.services import tasks as task_rules
from domain.services.adventure import STAGES


@dataclass(frozen=True, slots=True)
class TaskView:
    task: TaskDef
    status: task_rules.TaskStatus
    rewarded: bool


@dataclass(frozen=True, slots=True)
class AnswerResult:
    correct: bool
    explanation: str
    lesson_done: bool
    answered: int
    total: int


def _solved_questions(progress: TaskProgress) -> tuple[list[str], bool]:
    answered = list(progress.data.get("answered", []))  # type: ignore[arg-type]
    if len(answered) == progress.progress:
        return answered, False
    # Older builds marked wrong attempts as answered. Restart those unfinished lessons.
    progress.progress = 0
    progress.data = {**progress.data, "answered": []}
    progress.done_at = None
    return [], True


async def _facts(
    uow: UnitOfWork, state: GameState, lesson_slug: str | None, adventure: bool = False
) -> task_rules.WeekFacts:
    week = state.week
    quiz_total = quiz_correct = 0
    if lesson_slug:
        if adventure:
            quiz_total = STAGES
        else:
            questions = await uow.tasks.list_questions(lesson_slug)
            quiz_total = len(questions)
        progress = await uow.tasks.get_progress(state.player.id, week.id, lesson_slug)
        quiz_correct = progress.progress if progress else 0
    return task_rules.WeekFacts(
        week=week,
        quiz_correct=quiz_correct,
        quiz_total=quiz_total,
        care_days=await uow.log.care_days(state.player.id, week.id),
        discount_purchases=await uow.shop.count_discount_purchases(state.player.id, week.id),
        deposits=await uow.log.sum_amount(state.player.id, week.id, ActionKind.DEPOSIT),
        week_closed=week.closed_at is not None,
        need_purchases=await uow.shop.count_need_purchases(state.player.id, week.id),
    )


async def list_tasks(uow: UnitOfWork, player_id: UUID) -> list[TaskView]:
    async with uow:
        state = await load_state(uow, player_id)
        views = []
        for task in await uow.tasks.list_defs():
            scaled = task_rules.scale_task(task, state.week.number)
            lesson = scaled.slug if scaled.kind is TaskKind.LESSON else None
            status = task_rules.evaluate(
                scaled, await _facts(uow, state, lesson, bool(scaled.params.get("adventure")))
            )
            progress = await uow.tasks.get_progress(player_id, state.week.id, scaled.slug)
            views.append(TaskView(scaled, status, bool(progress and progress.rewarded_at)))
        return views


async def list_questions(uow: UnitOfWork, player_id: UUID, lesson_slug: str) -> list[QuizQuestion]:
    async with uow:
        state = await load_state(uow, player_id)
        questions = await uow.tasks.list_questions(lesson_slug)
        if not questions:
            raise NotFound("Урок не найден")
        progress = await uow.tasks.get_progress(player_id, state.week.id, lesson_slug)
        solved = set()
        if progress:
            answered, reset = _solved_questions(progress)
            solved = set(answered)
            if reset:
                await uow.tasks.upsert_progress(progress)
                await uow.commit()
        return [question for question in questions if question.slug not in solved]


async def answer(
    uow: UnitOfWork,
    player_id: UUID,
    lesson_slug: str,
    question_slug: str,
    index: int | None,
    value: int | None = None,
) -> AnswerResult:
    async with uow:
        state = await load_state(uow, player_id)
        questions = await uow.tasks.list_questions(lesson_slug)
        question = next((q for q in questions if q.slug == question_slug), None)
        if question is None:
            raise NotFound("Вопрос не найден")
        progress = await uow.tasks.get_progress(
            player_id, state.week.id, lesson_slug
        ) or TaskProgress(player_id, state.week.id, lesson_slug)
        answered, _ = _solved_questions(progress)
        if question_slug in answered:
            raise RuleViolation("На этот вопрос ты уже ответил")
        if question.activity == "COINS" and value is not None:
            expected = re.search(r"\d+", question.options[question.right_index])
            if expected is None:
                raise RuleViolation("Вопрос с монетами настроен неверно")
            correct = value == int(expected.group())
        elif index is not None and index < len(question.options):
            correct = index == question.right_index
        else:
            raise RuleViolation("Выбери ответ")
        if correct:
            answered.append(question_slug)
            progress.data = {**progress.data, "answered": answered, "last_mistake": None}
            progress.progress += 1
        else:
            progress.data = {
                **progress.data,
                "last_mistake": {
                    "question_slug": question_slug,
                    "selected": value if question.activity == "COINS" else index,
                },
            }
        done = progress.progress >= len(questions)
        if done and progress.done_at is None:
            progress.done_at = datetime.now(UTC)
        await uow.tasks.upsert_progress(progress)
        await learning.record_attempt(uow, player_id, lesson_slug, correct)
        await uow.commit()
        explanation = question.explanation if correct else "Ответ пока не совпал. Спроси питомца."
        return AnswerResult(correct, explanation, done, len(answered), len(questions))


async def claim(uow: UnitOfWork, player_id: UUID, slug: str) -> GameState:
    """Забрать награду за выполненное задание. Один раз на неделю."""
    async with uow:
        state = await load_state(uow, player_id)
        task = await uow.tasks.get_def(slug)
        if task is None:
            raise NotFound("Задание не найдено")
        scaled = task_rules.scale_task(task, state.week.number)
        lesson = slug if scaled.kind is TaskKind.LESSON else None
        status = task_rules.evaluate(
            scaled, await _facts(uow, state, lesson, bool(scaled.params.get("adventure")))
        )
        if not status.done:
            raise RuleViolation("Задание ещё не выполнено")
        progress = await uow.tasks.get_progress(player_id, state.week.id, slug) or TaskProgress(
            player_id, state.week.id, slug, progress=status.progress
        )
        if progress.rewarded_at is not None:
            raise RuleViolation("Награда за это задание уже получена")
        now = datetime.now(UTC)
        progress.done_at = progress.done_at or now
        progress.rewarded_at = now
        state.player.free_coins += scaled.reward
        await uow.tasks.upsert_progress(progress)
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.TASK_REWARD,
                amount=scaled.reward,
                note=f"Награда: {scaled.title}",
                meta={"slug": slug},
            )
        )
        await uow.players.save(state.player)
        await uow.commit()
        return state
