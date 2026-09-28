from fastapi import APIRouter

from api.deps import LlmDep, PlayerIdDep, UowDep
from api.schemas.adventures import AdventureActionIn, AdventureOut
from application.use_cases import adventures, ai

router = APIRouter(prefix="/adventures", tags=["Экспедиции"])


@router.get("/{slug}", response_model=AdventureOut)
async def get_adventure(
    slug: str, player_id: PlayerIdDep, uow: UowDep, llm: LlmDep
) -> AdventureOut:
    episode, state, rewarded = await adventures.get(uow, player_id, slug)
    reaction = await ai.adventure_reaction(uow, llm, player_id, slug, state)
    return AdventureOut.from_state(episode, state, rewarded, reaction.text)


@router.post("/{slug}/play", response_model=AdventureOut)
async def play_adventure(
    slug: str, body: AdventureActionIn, player_id: PlayerIdDep, uow: UowDep, llm: LlmDep
) -> AdventureOut:
    episode, state, rewarded = await adventures.advance(
        uow,
        player_id,
        slug,
        body.expected_stage,
        food=body.food,
        water=body.water,
        reserve=body.reserve,
        choice_id=body.choice_id,
        amount=body.amount,
    )
    reaction = await ai.adventure_reaction(uow, llm, player_id, slug, state)
    return AdventureOut.from_state(episode, state, rewarded, reaction.text)


@router.post("/{slug}/restart", response_model=AdventureOut)
async def restart_adventure(slug: str, player_id: PlayerIdDep, uow: UowDep) -> AdventureOut:
    episode, state, rewarded = await adventures.restart(uow, player_id, slug)
    return AdventureOut.from_state(episode, state, rewarded)
