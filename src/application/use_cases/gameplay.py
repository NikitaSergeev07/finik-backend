"""Игровые сценарии: состояние, план, уход, конец дня."""

from datetime import timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from application.dto import CareResult, DayResult, GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from application.use_cases.calendar import game_now
from core.errors import Forbidden, RuleViolation
from domain import rules
from domain.entities import LogEntry
from domain.enums import ActionKind, Category
from domain.services import care, planning
from domain.services.growth import DayOutcome


async def get_state(uow: UnitOfWork, player_id: UUID) -> GameState:
    async with uow:
        return await load_state(uow, player_id)


async def set_plan(uow: UnitOfWork, player_id: UUID, planned: dict[Category, int]) -> GameState:
    async with uow:
        state = await load_state(uow, player_id)
        if state.week.plan_confirmed and any(
            planned[cat] < state.week.entry(cat).planned for cat in Category
        ):
            raise RuleViolation("Подтверждённый план можно только пополнять свободными монетами")
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
        if not state.week.plan_confirmed:
            raise RuleViolation("Сначала утверди план недели")
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


async def topup_plan(uow: UnitOfWork, player_id: UUID, additions: dict[Category, int]) -> GameState:
    async with uow:
        state = await load_state(uow, player_id)
        if any(amount < 0 for amount in additions.values()):
            raise RuleViolation("Пополнение не может быть отрицательным")
        totals = {cat: state.week.entry(cat).planned + additions.get(cat, 0) for cat in Category}
        planning.apply_plan(state.player, state.week, totals)
        await uow.weeks.save(state.week)
        await uow.players.save(state.player)
        await uow.commit()
        return state


async def deposit(uow: UnitOfWork, player_id: UUID, amount: int) -> GameState:
    if amount <= 0:
        raise RuleViolation("Отложить можно только положительную сумму")
    async with uow:
        state = await load_state(uow, player_id)
        if not state.week.plan_confirmed:
            raise RuleViolation("Сначала утверди план недели")
        saving = state.week.entry(Category.SAVE)
        if saving.left < amount:
            raise RuleViolation(f"В копилке недели только {saving.left} монет")
        saving.spent += amount
        state.goal.saved += amount
        if state.goal.saved >= state.goal.target:
            state.goal.achieved_at = game_now(state.player)
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.DEPOSIT,
                amount=amount,
                category=Category.SAVE,
                note="Отложено в мечту",
                meta={"goal_slug": state.goal.catalog_slug},
            )
        )
        await uow.weeks.save(state.week)
        await uow.goals.save(state.goal)
        await uow.commit()
        return state


async def withdraw(uow: UnitOfWork, player_id: UUID, amount: int) -> GameState:
    if amount <= 0:
        raise RuleViolation("Снять можно только положительную сумму")
    async with uow:
        state = await load_state(uow, player_id)
        if amount > state.goal.saved:
            raise RuleViolation(f"В этой цели только {state.goal.saved} монет")
        state.goal.saved -= amount
        if state.goal.saved < state.goal.target:
            state.goal.achieved_at = None
        state.week.entry(Category.PLAY).planned += amount
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.WITHDRAW,
                amount=amount,
                category=Category.PLAY,
                note="Из цели в бюджет развлечений",
                meta={"goal_slug": state.goal.catalog_slug},
            )
        )
        await uow.goals.save(state.goal)
        await uow.weeks.save(state.week)
        await uow.commit()
        return state


async def advance_demo(
    uow: UnitOfWork, player_id: UUID, *, days: int = 1, to_week_end: bool = False
) -> GameState:
    async with uow:
        state = await load_state(uow, player_id)
        if state.player.mode != "demo":
            raise Forbidden("Пропуск времени доступен только в деморежиме")
        if not 1 <= days <= 31:
            raise RuleViolation("За один раз можно пропустить от 1 до 31 дня")
        local_now = game_now(state.player).astimezone(ZoneInfo(state.player.timezone))
        count = 7 - local_now.weekday() if to_week_end else days
        target = local_now + timedelta(days=count)
        if to_week_end:
            target = target.replace(hour=0, minute=0, second=0, microsecond=0)
        state.player.clock = {**state.player.clock, "demo_now": target.isoformat()}
        await uow.players.save(state.player)
        # Re-load within the SAME lock and transaction, then settle virtual calendar days.
        result = await load_state(uow, player_id)
        await uow.commit()
        return result


async def end_day(uow: UnitOfWork, player_id: UUID) -> DayResult:
    # Preserve the legacy response envelope, with the same server-side demo guard.
    async with uow:
        before = await load_state(uow, player_id)
        if before.player.mode != "demo":
            raise Forbidden("Пропуск времени доступен только в деморежиме")
        number, xp = before.week.number, before.pet.xp
    state = await advance_demo(uow, player_id)
    finished = state.week.number != number
    return DayResult(DayOutcome(state.week.day, state.pet.xp - xp, finished), None, state)
