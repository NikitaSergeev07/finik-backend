"""Покупка в лавке: строго из своей статьи, без добора из копилки. Цены — с множителем недели."""

from dataclasses import dataclass, replace
from math import ceil

from core.errors import RuleViolation
from domain import rules
from domain.entities import Pet, ShopItem, Week
from domain.enums import Category


@dataclass(frozen=True, slots=True)
class PurchaseOutcome:
    item: ShopItem
    restored: int
    xp_gained: int


def extra_price(week: Week, category: Category) -> int:
    raw = week.modifiers.get("price_delta") or {}
    return int(dict(raw).get(category.value, 0))


def with_week_price(item: ShopItem, week: Week) -> ShopItem:
    """Цена на витрине: множитель недели, надбавка события, скидка распродажи."""
    extra = extra_price(week, item.category)
    scaled = rules.scaled_cost(item.cost, week.number, extra)
    display_old = None
    if item.old_cost is not None:
        display_old = max(item.old_cost, rules.scaled_cost(item.old_cost, week.number, extra))
        if display_old <= scaled:
            display_old = item.old_cost if item.old_cost > scaled else None
    sale_pct = min(10, max(0, int(week.modifiers.get("sale_percent") or 0)))
    if sale_pct > 0:
        discounted = max(1, ceil(scaled * (100 - sale_pct) / 100))
        if discounted < scaled:
            display_old = max(display_old or 0, scaled)
            scaled = discounted
    old = display_old if display_old and display_old > scaled else None
    return replace(item, cost=scaled, old_cost=old)


def is_visible(item: ShopItem, unlocked: list[str]) -> bool:
    return (not item.hidden) or item.slug in unlocked


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
