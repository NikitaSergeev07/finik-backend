from fastapi import APIRouter

from finik.api.deps import SettingsDep, UowDep
from finik.api.schemas.game import DeviceLoginIn, TokenOut
from finik.application.use_cases import onboarding
from finik.core.security import issue_token

router = APIRouter(prefix="/auth", tags=["Вход"])


@router.post("/device", response_model=TokenOut, summary="Вход по идентификатору устройства")
async def login_by_device(body: DeviceLoginIn, uow: UowDep, settings: SettingsDep) -> TokenOut:
    """Ребёнок ничего не вводит. Телефон присылает свой идентификатор и получает токен."""
    player = await onboarding.register_device(uow, body.device_id)
    async with uow:
        has_pet = await uow.pets.get_by_player(player.id) is not None
    return TokenOut(token=issue_token(player.id, settings), has_pet=has_pet)
