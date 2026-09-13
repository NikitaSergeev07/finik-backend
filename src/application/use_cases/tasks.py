"""Задания недели: список с прогрессом, ответ на вопрос урока, получение награды."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import NotFound, RuleViolation
from domain.entities import LogEntry, QuizQuestion, TaskDef, TaskProgress
from domain.enums import ActionKind, TaskKind
from domain.services import tasks as task_rules


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


async def _facts(
    uow: UnitOfWork, state: GameState, lesson_slug: str | None
) -> task_rules.WeekFacts:
    week = state.week
    quiz_total = quiz_correct = 0
    if lesson_slug:
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
    )


async def list_tasks(uow: UnitOfWork, player_id: UUID) -> list[TaskView]:
    async with uow:
        state = await load_state(uow, player_id)
        views = []
        for task in await uow.tasks.list_defs():
            lesson = task.slug if task.kind is TaskKind.LESSON else None
            status = task_rules.evaluate(task, await _facts(uow, state, lesson))
            progress = await uow.tasks.get_progress(player_id, state.week.id, task.slug)
            views.append(TaskView(task, status, bool(progress and progress.rewarded_at)))
        return views


async def list_questions(uow: UnitOfWork, player_id: UUID, lesson_slug: str) -> list[QuizQuestion]:
    async with uow:
        await load_state(uow, player_id)
        questions = await uow.tasks.list_questions(lesson_slug)
        if not questions:
            raise NotFound("Урок не найден")
        return questions


async def answer(
    uow: UnitOfWork, player_id: UUID, lesson_slug: str, question_slug: str, index: int
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
        answered: list[str] = list(progress.data.get("answered", []))  # type: ignore[arg-type]
        if question_slug in answered:
            raise RuleViolation("На этот вопрос ты уже ответил")
        correct = index == question.right_index
        answered.append(question_slug)
        progress.data = {**progress.data, "answered": answered}
        if correct:
            progress.progress += 1
        done = progress.progress >= len(questions)
        if done and progress.done_at is None:
            progress.done_at = datetime.now(UTC)
        await uow.tasks.upsert_progress(progress)
        await uow.commit()
        return AnswerResult(correct, question.explanation, done, len(answered), len(questions))


async def claim(uow: UnitOfWork, player_id: UUID, slug: str) -> GameState:
    """Забрать награду за выполненное задание. Один раз на неделю."""
    async with uow:
        state = await load_state(uow, player_id)
        task = await uow.tasks.get_def(slug)
        if task is None:
            raise NotFound("Задание не найдено")
        lesson = slug if task.kind is TaskKind.LESSON else None
        status = task_rules.evaluate(task, await _facts(uow, state, lesson))
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
        state.player.free_coins += task.reward
        await uow.tasks.upsert_progress(progress)
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.TASK_REWARD,
                amount=task.reward,
                note=f"Награда: {task.title}",
                meta={"slug": slug},
            )
        )
        await uow.players.save(state.player)
        await uow.commit()
        return state
