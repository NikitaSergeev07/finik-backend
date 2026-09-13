"""Покупка в лавке: строго из своей статьи, без добора из копилки."""

from dataclasses import dataclass

from core.errors import RuleViolation
from domain import rules
from domain.entities import Pet, ShopItem, Week


@dataclass(frozen=True, slots=True)
class PurchaseOutcome:
    item: ShopItem
    restored: int
    xp_gained: int


def purchase(pet: Pet, week: Week, item: ShopItem) -> PurchaseOutcome:
    entry = week.entry(item.category)
    if entry.left < item.cost:
        raise RuleViolation(
            f"В статье «{item.category}» осталось {entry.left}, а «{item.name}» стоит {item.cost}"
        )
    entry.spent += item.cost
    restored = 0
    if item.category.is_need and item.restore:
        before = pet.needs[item.category]
        pet.needs[item.category] = min(rules.NEED_MAX, before + item.restore)
        restored = pet.needs[item.category] - before
    pet.xp += item.xp_bonus
    return PurchaseOutcome(item, restored, item.xp_bonus)
