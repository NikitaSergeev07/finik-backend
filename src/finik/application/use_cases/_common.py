"""Общие шаги сценариев: загрузить полное состояние игрока или упасть понятной ошибкой."""

from uuid import UUID

from finik.application.dto import GameState
from finik.application.ports import UnitOfWork
from finik.core.errors import NotFound


async def load_state(uow: UnitOfWork, player_id: UUID) -> GameState:
    player = await uow.players.get(player_id)
    if player is None:
        raise NotFound("Игрок не найден")
    pet = await uow.pets.get_by_player(player_id)
    week = await uow.weeks.get_current(player_id)
    goal = await uow.goals.get_active(player_id)
    if pet is None or week is None or goal is None:
        raise NotFound("Питомец ещё не создан. Пройди знакомство")
    return GameState(player, pet, week, goal)
