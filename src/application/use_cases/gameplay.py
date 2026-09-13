"""Игровые сценарии: состояние, план, уход, конец дня."""

from uuid import UUID, uuid4

from application.dto import CareResult, DayResult, GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import RuleViolation
from domain import rules
from domain.entities import LogEntry, PlanEntry, Week
from domain.enums import ActionKind, Category
from domain.services import care, growth, planning


async def get_state(uow: UnitOfWork, player_id: UUID) -> GameState:
    async with uow:
        return await load_state(uow, player_id)


async def set_plan(uow: UnitOfWork, player_id: UUID, planned: dict[Category, int]) -> GameState:
    async with uow:
        state = await load_state(uow, player_id)
        planning.apply_plan(state.player, state.week, planned)
        await uow.weeks.save(state.week)
        await uow.players.save(state.player)
        await uow.commit()
        return state


async def care_for_pet(uow: UnitOfWork, player_id: UUID, category: Category) -> CareResult:
    async with uow:
        state = await load_state(uow, player_id)
        outcome = care.perform_care(state.pet, state.week, category)
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.CARE,
                amount=outcome.cost,
                category=category,
                note=rules.CARE_ACTIONS[category].label,
                meta={"from_savings": outcome.from_savings, "xp": outcome.xp_gained},
            )
        )
        if outcome.from_savings:
            await uow.log.add(
                LogEntry(
                    player_id,
                    state.week.id,
                    state.week.day,
                    ActionKind.OVERRUN,
                    amount=outcome.cost,
                    category=category,
                    note=f"Перерасход по статье «{category}»: взято из копилки",
                )
            )
        await uow.pets.save(state.pet)
        await uow.weeks.save(state.week)
        await uow.commit()
        return CareResult(outcome, state)


async def deposit(uow: UnitOfWork, player_id: UUID, amount: int) -> GameState:
    """Отложить свободные монеты прямо в мечту, минуя план."""
    if amount <= 0:
        raise RuleViolation("Отложить можно только положительную сумму")
    async with uow:
        state = await load_state(uow, player_id)
        if state.player.free_coins < amount:
            raise RuleViolation(f"Свободных монет только {state.player.free_coins}")
        state.player.free_coins -= amount
        state.goal.saved += amount
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.DEPOSIT,
                amount=amount,
                category=Category.SAVE,
                note="Отложено в мечту",
            )
        )
        await uow.players.save(state.player)
        await uow.goals.save(state.goal)
        await uow.commit()
        return state


async def end_day(uow: UnitOfWork, player_id: UUID) -> DayResult:
    async with uow:
        state = await load_state(uow, player_id)
        day = growth.end_day(state.pet, state.week)
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                day.day - 1,
                ActionKind.DAY_END,
                note="День завершён",
                meta={"xp": day.xp_gained},
            )
        )
        week_outcome = None
        week = state.week
        if day.week_finished:
            week_outcome = growth.close_week(state.player, state.pet, week, state.goal)
            week.closed_at = _now()
            await uow.log.add(
                LogEntry(
                    player_id,
                    week.id,
                    rules.DAYS_IN_WEEK,
                    ActionKind.WEEK_CLOSE,
                    amount=week_outcome.saved,
                    note=f"Неделя {week.number} закрыта",
                    meta={"overrun": week_outcome.overrun, "xp": week_outcome.xp_gained},
                )
            )
            if week_outcome.goal_achieved:
                state.goal.achieved_at = _now()
            await uow.weeks.save(week)
            state.player.free_coins += state.player.weekly_income
            week = Week(
                uuid4(),
                player_id,
                week.number + 1,
                state.player.weekly_income,
                day=1,
                entries={cat: PlanEntry(cat, 0) for cat in Category},
            )
            await uow.weeks.add(week)
            await uow.goals.save(state.goal)
        else:
            await uow.weeks.save(week)
        await uow.pets.save(state.pet)
        await uow.players.save(state.player)
        await uow.commit()
        new_state = GameState(state.player, state.pet, week, state.goal)
        return DayResult(day, week_outcome, new_state)


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
