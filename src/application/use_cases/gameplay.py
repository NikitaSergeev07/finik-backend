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
        if state.week.plan_confirmed:
            raise RuleViolation("План уже утверждён. Менять можно на следующей неделе.")
        planning.apply_plan(state.player, state.week, planned)
        await uow.weeks.save(state.week)
        await uow.players.save(state.player)
        await uow.commit()
        return state


async def confirm_plan(uow: UnitOfWork, player_id: UUID) -> GameState:
    async with uow:
        state = await load_state(uow, player_id)
        if state.week.plan_confirmed:
            raise RuleViolation("План уже утверждён")
        state.week.plan_confirmed = True
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.PLAN_CONFIRM,
                note="План недели утверждён",
            )
        )
        await uow.weeks.save(state.week)
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
                meta={"xp": day.xp_gained, "wilt": day.wilt_xp_lost},
            )
        )
        if day.wilt_xp_lost:
            await uow.log.add(
                LogEntry(
                    player_id,
                    state.week.id,
                    day.day - 1,
                    ActionKind.WILT,
                    amount=day.wilt_xp_lost,
                    note="Росток завял: потребность на нуле, потерян опыт",
                    meta={"xp_lost": day.wilt_xp_lost},
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
                    meta={
                        "overrun": week_outcome.overrun,
                        "xp": week_outcome.xp_gained,
                        "interest": week_outcome.interest,
                        "cashback": week_outcome.cashback,
                    },
                )
            )
            if week_outcome.interest:
                await uow.log.add(
                    LogEntry(
                        player_id,
                        week.id,
                        rules.DAYS_IN_WEEK,
                        ActionKind.INTEREST,
                        amount=week_outcome.interest,
                        category=Category.SAVE,
                        note=f"Копилка подросла на {rules.SAVINGS_INTEREST_PCT}%",
                    )
                )
            if week_outcome.cashback:
                await uow.log.add(
                    LogEntry(
                        player_id,
                        week.id,
                        rules.DAYS_IN_WEEK,
                        ActionKind.CASHBACK,
                        amount=week_outcome.cashback,
                        note="Редкий росток вернул монетку с остатка игр",
                    )
                )
            if week_outcome.goal_achieved:
                state.goal.achieved_at = _now()
            await uow.weeks.save(week)
            state.player.free_coins += rules.STREAK_BONUS
            await uow.log.add(
                LogEntry(
                    player_id,
                    week.id,
                    rules.DAYS_IN_WEEK,
                    ActionKind.STREAK,
                    amount=rules.STREAK_BONUS,
                    note="7 дней подряд",
                )
            )
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
            await uow.log.add(
                LogEntry(
                    player_id,
                    week.id,
                    1,
                    ActionKind.INCOME,
                    amount=state.player.weekly_income,
                    note=f"Пришёл доход {state.player.weekly_income}",
                )
            )
            await uow.goals.save(state.goal)
        else:
            await uow.weeks.save(week)
        await uow.pets.save(state.pet)
        await uow.players.save(state.player)
        await uow.commit()
        income_note = f"Пришёл доход {state.player.weekly_income}"
        new_state = GameState(
            state.player,
            state.pet,
            week,
            state.goal,
            last_income=state.player.weekly_income if day.week_finished else state.last_income,
            last_income_note=income_note if day.week_finished else state.last_income_note,
            last_purchase_note=state.last_purchase_note,
            last_purchase_amount=state.last_purchase_amount,
        )
        return DayResult(day, week_outcome, new_state)


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
