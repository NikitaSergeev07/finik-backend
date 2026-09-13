"""Знакомство: вход по устройству и создание ростка с первой неделей."""

from uuid import UUID, uuid4

from finik.application.dto import GameState
from finik.application.ports import UnitOfWork
from finik.core.errors import Conflict, RuleViolation
from finik.domain import rules
from finik.domain.entities import Goal, Pet, PlanEntry, Player, Week
from finik.domain.enums import Category, Species
from finik.domain.services.planning import advised_plan, apply_plan


async def register_device(uow: UnitOfWork, device_id: str) -> Player:
    async with uow:
        player = await uow.players.get_by_device(device_id)
        if player is None:
            player = Player(uuid4(), device_id, weekly_income=rules.INCOME_OPTIONS[1], free_coins=0)
            await uow.players.add(player)
            await uow.commit()
        return player


async def create_pet(
    uow: UnitOfWork, player_id: UUID, name: str, species: Species, weekly_income: int
) -> GameState:
    if weekly_income not in rules.INCOME_OPTIONS:
        raise RuleViolation(f"Доход в неделю бывает только {rules.INCOME_OPTIONS}")
    name = name.strip()
    if not 1 <= len(name) <= 20:
        raise RuleViolation("Имя питомца — от 1 до 20 символов")

    async with uow:
        player = await uow.players.get(player_id)
        if player is None:
            raise Conflict("Сначала войди по устройству")
        if await uow.pets.get_by_player(player_id) is not None:
            raise Conflict("Питомец уже есть")

        player.weekly_income = weekly_income
        player.free_coins = weekly_income
        pet = Pet(
            uuid4(),
            player_id,
            name,
            species,
            xp=0,
            needs={cat: rules.NEED_START for cat in Category if cat.is_need},
        )
        week = Week(
            uuid4(),
            player_id,
            number=1,
            income=weekly_income,
            day=1,
            entries={cat: PlanEntry(cat, 0) for cat in Category},
        )
        apply_plan(player, week, advised_plan(weekly_income))
        goal = Goal(uuid4(), player_id, rules.DEFAULT_GOAL_TITLE, rules.DEFAULT_GOAL_TARGET, 0)

        await uow.pets.add(pet)
        await uow.weeks.add(week)
        await uow.goals.add(goal)
        await uow.players.save(player)
        await uow.commit()
        return GameState(player, pet, week, goal)
