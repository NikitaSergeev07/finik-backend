"""Внешность ростка: надеть купленный наряд, снять, сменить цвет."""

from core.errors import RuleViolation
from domain import rules
from domain.entities import Pet, ShopItem

POT = "pot"
ACCESSORY = "accessory"


def apply_customize(
    pet: Pet,
    owned: set[str],
    catalog: dict[str, ShopItem],
    *,
    pot: str | None = None,
    accessory: str | None = None,
    look_variant: int | None = None,
) -> None:
    if look_variant is not None:
        pet.look_variant = rules.look_variant_or_raise(look_variant)
    if pot is not None:
        pet.equipped_pot = _equip(owned, catalog, pot, POT)
    if accessory is not None:
        pet.equipped_accessory = _equip(owned, catalog, accessory, ACCESSORY)


def _equip(owned: set[str], catalog: dict[str, ShopItem], slug: str, slot: str) -> str:
    if slug == "":
        return ""
    item = catalog.get(slug)
    if item is None or item.slot != slot:
        label = "горшок" if slot == POT else "аксессуар"
        raise RuleViolation(f"Такого наряда нет. Выбери {label} из лавки.")
    if slug not in owned:
        raise RuleViolation(f"Сначала купи «{item.name}» в лавке за монеты игр")
    return slug
