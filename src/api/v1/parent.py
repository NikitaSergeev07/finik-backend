from fastapi import APIRouter

from api.deps import PlayerIdDep, SettingsDep, UowDep
from api.schemas.parent import BonusIn, BonusOut
from application.use_cases import parent as use_parent

router = APIRouter(prefix="/parent", tags=["Родитель"])


@router.post("/bonus", response_model=BonusOut, summary="Премия за дело")
async def bonus(
    body: BonusIn, player_id: PlayerIdDep, uow: UowDep, settings: SettingsDep
) -> BonusOut:
    """Монеты начисляет родитель: тот же JWT устройства плюс PIN из настроек сервера."""
    state = await use_parent.grant_bonus(
        uow, player_id, body.amount, body.reason, body.pin, settings.parent_pin
    )
    return BonusOut.from_state(state, body.amount, body.reason.strip())
