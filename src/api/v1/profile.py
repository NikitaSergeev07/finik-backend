from fastapi import APIRouter, status

from api.deps import PlayerIdDep, UowDep
from api.schemas.game import StateOut
from api.schemas.social import BadgeOut, ProfileOut, SettingsIn
from application.use_cases import badges, profile

router = APIRouter(prefix="/profile", tags=["Профиль"])


@router.get("", response_model=ProfileOut, summary="Профиль и итоги за всё время")
async def get_profile(player_id: PlayerIdDep, uow: UowDep) -> ProfileOut:
    return ProfileOut.from_view(await profile.get_profile(uow, player_id))


@router.patch("", response_model=StateOut, summary="Настройки: доход, звуки, события")
async def update_settings(body: SettingsIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    """Новый доход вступает в силу со следующей недели."""
    state = await profile.update_settings(
        uow, player_id, body.weekly_income, body.sound_on, body.event_mode
    )
    return StateOut.from_state(state)


@router.get("/badges", response_model=list[BadgeOut], summary="Достижения с прогрессом")
async def list_badges(player_id: PlayerIdDep, uow: UowDep) -> list[BadgeOut]:
    return [BadgeOut.from_view(v) for v in await badges.list_badges(uow, player_id)]


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT, summary="Начать заново")
async def reset(player_id: PlayerIdDep, uow: UowDep) -> None:
    """Стирает ростка, недели, мечту и журнал. Токен устройства остаётся рабочим."""
    await profile.reset(uow, player_id)
