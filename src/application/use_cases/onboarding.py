"""Знакомство: вход по устройству и создание ростка с первой неделей."""

from uuid import UUID, uuid4

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import Conflict, RuleViolation
from domain import rules
from domain.entities import Goal, LogEntry, Pet, PlanEntry, Player, Week
from domain.enums import ActionKind, Category, Species
from domain.services.planning import advised_plan, apply_plan


async def register_device(uow: UnitOfWork, device_id: str) -> Player:
    async with uow:
        player = await uow.players.get_by_device(device_id)
        if player is None:
            player = Player(uuid4(), device_id, weekly_income=rules.INCOME_OPTIONS[1], free_coins=0)
            await uow.players.add(player)
            await uow.commit()
        return player


async def create_pet(
    uow: UnitOfWork,
    player_id: UUID,
    name: str,
    species: Species,
    weekly_income: int,
    *,
    goal_slug: str | None = None,
    look_variant: int = 0,
) -> GameState:
    if weekly_income not in rules.INCOME_OPTIONS:
        raise RuleViolation(f"Доход в неделю бывает только {rules.INCOME_OPTIONS}")
    name = name.strip()
    if not 1 <= len(name) <= 20:
        raise RuleViolation("Имя питомца — от 1 до 20 символов")
    option = rules.goal_by_slug(goal_slug)
    look = rules.look_variant_or_raise(look_variant)

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
            look_variant=look,
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
        goal = Goal(
            uuid4(),
            player_id,
            option.title,
            option.target,
            0,
            catalog_slug=option.slug,
        )

        await uow.pets.add(pet)
        await uow.weeks.add(week)
        await uow.goals.add(goal)
        await uow.players.save(player)
        await uow.log.add(
            LogEntry(
                player_id,
                week.id,
                week.day,
                ActionKind.INCOME,
                amount=weekly_income,
                note=f"Пришёл доход {weekly_income}",
            )
        )
        await uow.commit()
        return GameState(
            player,
            pet,
            week,
            goal,
            last_income=weekly_income,
            last_income_note=f"Пришёл доход {weekly_income}",
        )


async def select_goal(uow: UnitOfWork, player_id: UUID, slug: str) -> GameState:
    option = rules.goal_by_slug(slug)
    async with uow:
        state = await load_state(uow, player_id)
        state.goal.title = option.title
        state.goal.target = option.target
        state.goal.catalog_slug = option.slug
        state.goal.achieved_at = _now() if state.goal.saved >= option.target else None
        await uow.goals.save(state.goal)
        await uow.commit()
        return state


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
