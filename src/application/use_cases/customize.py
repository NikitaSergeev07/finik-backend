"""Смена облика: только купленные наряды, цвет 0–2 всегда можно."""

from uuid import UUID

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from domain.services import look as look_rules


async def customize(
    uow: UnitOfWork,
    player_id: UUID,
    *,
    pot: str | None = None,
    accessory: str | None = None,
    look_variant: int | None = None,
    accessories: list[str] | None = None,
) -> GameState:
    async with uow:
        state = await load_state(uow, player_id)
        items = {item.slug: item for item in await uow.shop.list_items()}
        look_rules.apply_customize(
            state.pet,
            set(state.owned_cosmetics),
            items,
            pot=pot,
            accessory=accessory,
            look_variant=look_variant,
        )
        if accessories is not None:
            state.pet.accessories = look_rules.validate_accessories(accessories)
        elif accessory is not None:
            owl_accessory = {
                "hat_leaf": "hat",
                "scarf_knit": "bandana",
                "glasses_round": "medal",
                "charm_can": "backpack",
            }.get(accessory)
            if owl_accessory:
                state.pet.accessories = sorted(set((*state.pet.accessories, owl_accessory)))
        await uow.pets.save(state.pet)
        await uow.commit()
        return state
