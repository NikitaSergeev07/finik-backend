"""Общие шаги сценариев: загрузить полное состояние игрока или упасть понятной ошибкой."""

from uuid import UUID

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases.calendar import synchronize
from core.errors import NotFound
from domain.enums import ActionKind


async def load_state(uow: UnitOfWork, player_id: UUID) -> GameState:
    player = await uow.players.get(player_id)
    if player is None:
        raise NotFound("Игрок не найден")
    pet = await uow.pets.get_by_player(player_id)
    week = await uow.weeks.get_current(player_id)
    goal = await uow.goals.get_active(player_id)
    if pet is None or week is None or goal is None:
        raise NotFound("Питомец ещё не создан. Пройди знакомство")
    week = await synchronize(uow, player, pet, week, goal)
    goals = await uow.goals.list_all(player_id)
    # Use the same goal object so subsequent commands update the list response too.
    goals = [goal if item.id == goal.id else item for item in goals]
    income = await uow.log.latest(player_id, ActionKind.INCOME)
    purchase = await uow.log.latest(player_id, ActionKind.PURCHASE)
    owned = tuple(await uow.shop.list_owned_slugs(player_id))
    return GameState(
        player,
        pet,
        week,
        goal,
        last_income=income.amount if income else week.income,
        last_income_note=income.note if income else f"Пришёл доход {week.income}",
        last_purchase_note=purchase.note if purchase else "",
        last_purchase_amount=purchase.amount if purchase else 0,
        owned_cosmetics=owned,
        goals=tuple(goals),
    )
