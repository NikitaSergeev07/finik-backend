"""Профиль: итоги за всё время, настройки и сброс прогресса."""

from dataclasses import dataclass
from uuid import UUID

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import NotFound, RuleViolation
from domain import rules
from domain.enums import EventMode


@dataclass(frozen=True, slots=True)
class ProfileView:
    state: GameState
    earned_total: int
    saved_total: int
    weeks_done: int
    tasks_done: int


async def get_profile(uow: UnitOfWork, player_id: UUID) -> ProfileView:
    async with uow:
        state = await load_state(uow, player_id)
        closed = await uow.weeks.list_closed(player_id, limit=520)
        earned = await uow.log.earned_total(player_id)
        saved = sum(goal.saved for goal in state.goals)
        tasks_done = await uow.tasks.count_rewarded(player_id)
        return ProfileView(state, earned, saved, len(closed), tasks_done)


async def update_settings(
    uow: UnitOfWork,
    player_id: UUID,
    weekly_income: int | None,
    sound_on: bool | None,
    event_mode: EventMode | None = None,
) -> GameState:
    async with uow:
        state = await load_state(uow, player_id)
        if weekly_income is not None:
            if weekly_income not in rules.INCOME_OPTIONS:
                raise RuleViolation(f"Доход в неделю бывает только {rules.INCOME_OPTIONS}")
            state.player.weekly_income = weekly_income  # вступит в силу со следующей недели
        if sound_on is not None:
            state.player.sound_on = sound_on
        if event_mode is not None:
            state.player.event_mode = event_mode
        await uow.players.save(state.player)
        await uow.commit()
        return state


async def reset(uow: UnitOfWork, player_id: UUID) -> None:
    """Стереть ростка, недели, мечту и журнал. Учётная запись устройства остаётся."""
    async with uow:
        player = await uow.players.get(player_id)
        if player is None:
            raise NotFound("Игрок не найден")
        await uow.players.wipe_progress(player_id)
        player.free_coins = 0
        player.vaccinated_until = 0
        player.unlocked_shop = []
        player.clock = {}
        player.selected_goal_slug = rules.GOAL_CATALOG[0].slug
        await uow.players.save(player)
        await uow.commit()
