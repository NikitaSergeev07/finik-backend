"""Server-authoritative calendar. One player row lock protects the entire transition."""

from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from application.dto import GameState
from application.ports import UnitOfWork
from core.errors import RuleViolation
from domain import rules
from domain.entities import Goal, LogEntry, Pet, PlanEntry, Player, TaskProgress, Week
from domain.enums import ActionKind, Category, TaskKind
from domain.services import growth


def now_utc() -> datetime:
    return datetime.now(UTC)


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
        raise RuleViolation("Укажи часовой пояс IANA, например Europe/Moscow") from error
    return value


def game_now(player: Player) -> datetime:
    if player.mode == "demo" and player.clock.get("demo_now"):
        return datetime.fromisoformat(str(player.clock["demo_now"])).astimezone(UTC)
    return now_utc()


def local_date(player: Player) -> date:
    return game_now(player).astimezone(ZoneInfo(player.timezone)).date()


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_instant(player: Player, day: date) -> datetime:
    return datetime.combine(day, time.min, ZoneInfo(player.timezone)).astimezone(UTC)


def initialize_clock(player: Player) -> date:
    now = now_utc()
    day = now.astimezone(ZoneInfo(player.timezone)).date()
    player.clock = {"last_date": day.isoformat(), "elapsed_days": 0}
    if player.mode == "demo":
        player.clock["demo_now"] = now.isoformat()
    return day


def new_week(player: Player, number: int, day: date, *, income: int) -> Week:
    start = monday(day)
    return Week(
        uuid4(),
        player.id,
        number,
        income,
        day.weekday() + 1,
        {cat: PlanEntry(cat, 0) for cat in Category},
        modifiers={
            "calendar_start": start.isoformat(),
            "calendar_end": (start + timedelta(days=7)).isoformat(),
        },
    )


async def _settle_tasks(uow: UnitOfWork, state: GameState, at: datetime) -> None:
    """Claim completed rewards at closing, including plan tasks only decidable then."""
    from application.use_cases.tasks import _facts
    from domain.services import tasks as task_rules

    for task in await uow.tasks.list_defs():
        scaled = task_rules.scale_task(task, state.week.number)
        progress = await uow.tasks.get_progress(state.player.id, state.week.id, task.slug)
        if progress and progress.rewarded_at:
            continue
        lesson = task.slug if task.kind is TaskKind.LESSON else None
        status = task_rules.evaluate(
            scaled, await _facts(uow, state, lesson, bool(scaled.params.get("adventure")))
        )
        # An empty, never confirmed plan is not a completed budgeting exercise.
        if task.slug == "food_plan" and not state.week.plan_confirmed:
            continue
        if not status.done:
            continue
        progress = progress or TaskProgress(state.player.id, state.week.id, task.slug)
        progress.progress = status.progress
        progress.done_at = progress.done_at or at
        progress.rewarded_at = at
        state.player.free_coins += scaled.reward
        await uow.tasks.upsert_progress(progress)
        await uow.log.add(
            LogEntry(
                state.player.id,
                state.week.id,
                7,
                ActionKind.TASK_REWARD,
                amount=scaled.reward,
                note=f"Награда: {scaled.title}",
                meta={"slug": task.slug, "automatic_at_close": True},
            )
        )


async def synchronize(uow: UnitOfWork, player: Player, pet: Pet, week: Week, goal: Goal) -> Week:
    today = local_date(player)
    if not player.clock.get("last_date"):
        player.clock = {**player.clock, "last_date": today.isoformat(), "elapsed_days": 0}
    last = date.fromisoformat(str(player.clock["last_date"]))
    week.modifiers.setdefault("calendar_start", monday(last).isoformat())
    week.modifiers.setdefault("calendar_end", (monday(last) + timedelta(days=7)).isoformat())
    current_monday = monday(today)
    elapsed = int(player.clock.get("elapsed_days", 0))
    while last < today:
        outcome = growth.end_day(pet, week)
        await uow.log.add(
            LogEntry(
                player.id,
                week.id,
                last.weekday() + 1,
                ActionKind.DAY_END,
                note="День завершён по календарю",
                meta={
                    "date": last.isoformat(),
                    "xp": outcome.xp_gained,
                    "wilt": outcome.wilt_xp_lost,
                },
            )
        )
        if outcome.wilt_xp_lost:
            await uow.log.add(
                LogEntry(
                    player.id,
                    week.id,
                    last.weekday() + 1,
                    ActionKind.WILT,
                    amount=outcome.wilt_xp_lost,
                    note="Питомец загрустил: потребность на нуле",
                )
            )
        elapsed += 1
        if elapsed % rules.DAYS_IN_WEEK == 0:
            player.free_coins += rules.STREAK_BONUS
            await uow.log.add(
                LogEntry(
                    player.id,
                    week.id,
                    last.weekday() + 1,
                    ActionKind.STREAK,
                    amount=rules.STREAK_BONUS,
                    note="Бонус за семь игровых дней",
                )
            )
        last += timedelta(days=1)
        if last.weekday() == 0:
            at = week_instant(player, last)
            week.closed_at = at
            # Evaluate against pre-settlement SAVE; transferring it changes `left`.
            if week.income > 0:
                await _settle_tasks(uow, GameState(player, pet, week, goal), at)
            summary = growth.close_week(player, pet, week, goal)
            # Unvisited, unfunded weeks cannot grant discipline XP.
            if week.income == 0 and not week.plan_confirmed:
                pet.xp = max(0, pet.xp - summary.xp_gained)
                summary = replace(summary, xp_gained=0)
            if summary.goal_achieved:
                goal.achieved_at = at
            await uow.log.add(
                LogEntry(
                    player.id,
                    week.id,
                    7,
                    ActionKind.WEEK_CLOSE,
                    amount=summary.saved,
                    note=f"Неделя {week.number} закрыта",
                    meta={
                        "overrun": summary.overrun,
                        "xp": summary.xp_gained,
                        "interest": summary.interest,
                        "cashback": summary.cashback,
                    },
                )
            )
            if summary.interest:
                await uow.log.add(
                    LogEntry(
                        player.id,
                        week.id,
                        7,
                        ActionKind.INTEREST,
                        amount=summary.interest,
                        category=Category.SAVE,
                        note="5% от остатка копилки",
                    )
                )
            await uow.weeks.save(week)
            # Only the week containing this request gets an income. Skipped weeks get zero.
            income = player.weekly_income if last == current_monday else 0
            week = new_week(player, week.number + 1, last, income=income)
            await uow.weeks.add(week)
            if income:
                player.free_coins += income
                await uow.log.add(
                    LogEntry(
                        player.id,
                        week.id,
                        1,
                        ActionKind.INCOME,
                        amount=income,
                        note=f"Пришёл доход {income}",
                    )
                )
    week.day = today.weekday() + 1
    player.clock = {**player.clock, "last_date": last.isoformat(), "elapsed_days": elapsed}
    await uow.players.save(player)
    await uow.pets.save(pet)
    await uow.weeks.save(week)
    await uow.goals.save(goal)
    return week
