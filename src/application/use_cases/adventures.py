"""Load and advance a story mission for the current player and week."""

from datetime import UTC, datetime
from uuid import UUID

from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import NotFound, RuleViolation
from domain.entities import TaskProgress
from domain.services.adventure import EPISODES, STAGES, AdventureState, Episode, new_game, play


async def get(uow: UnitOfWork, player_id: UUID, slug: str) -> tuple[Episode, AdventureState, bool]:
    episode = EPISODES.get(slug)
    if episode is None:
        raise NotFound("Экспедиция не найдена")
    async with uow:
        game = await load_state(uow, player_id)
        progress = await uow.tasks.get_progress(player_id, game.week.id, slug)
        data = progress.data.get("adventure") if progress else None
        state = (
            AdventureState.from_data(data, episode) if isinstance(data, dict) else new_game(episode)
        )
        return episode, state, bool(progress and progress.rewarded_at)


async def advance(
    uow: UnitOfWork,
    player_id: UUID,
    slug: str,
    expected_stage: int,
    *,
    food: int | None = None,
    water: int | None = None,
    reserve: int | None = None,
    choice_id: str | None = None,
    amount: int | None = None,
) -> tuple[Episode, AdventureState, bool]:
    episode = EPISODES.get(slug)
    if episode is None:
        raise NotFound("Экспедиция не найдена")
    async with uow:
        game = await load_state(uow, player_id)
        progress = await uow.tasks.get_progress(player_id, game.week.id, slug) or TaskProgress(
            player_id, game.week.id, slug
        )
        data = progress.data.get("adventure")
        state = (
            AdventureState.from_data(data, episode) if isinstance(data, dict) else new_game(episode)
        )
        if expected_stage < state.stage:
            return episode, state, bool(progress.rewarded_at)
        if expected_stage != state.stage:
            raise RuleViolation("Обнови экспедицию и попробуй ещё раз")
        try:
            play(
                episode,
                state,
                food=food,
                water=water,
                reserve=reserve,
                choice_id=choice_id,
                amount=amount,
            )
        except ValueError as error:
            raise RuleViolation(str(error)) from error
        progress.progress = max(progress.progress, state.stage)
        progress.data = {**progress.data, "adventure": state.to_data()}
        if state.stage == STAGES:
            progress.done_at = datetime.now(UTC)
        await uow.tasks.upsert_progress(progress)
        await uow.commit()
        return episode, state, bool(progress.rewarded_at)


async def restart(
    uow: UnitOfWork, player_id: UUID, slug: str
) -> tuple[Episode, AdventureState, bool]:
    episode = EPISODES.get(slug)
    if episode is None:
        raise NotFound("Экспедиция не найдена")
    async with uow:
        game = await load_state(uow, player_id)
        progress = await uow.tasks.get_progress(player_id, game.week.id, slug)
        if progress is None:
            raise RuleViolation("Сначала пройди экспедицию")
        data = progress.data.get("adventure")
        if not isinstance(data, dict):
            raise RuleViolation("Сначала пройди экспедицию")
        state = AdventureState.from_data(data, episode)
        if state.stage < STAGES:
            raise RuleViolation("Сначала заверши экспедицию")
        fresh = new_game(episode)
        progress.data = {**progress.data, "adventure": fresh.to_data()}
        await uow.tasks.upsert_progress(progress)
        await uow.commit()
        return episode, fresh, bool(progress.rewarded_at)
