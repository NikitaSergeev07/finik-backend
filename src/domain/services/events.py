"""События дня: детерминированный выбор и применение последствий выбранного варианта."""

import hashlib
from dataclasses import dataclass, field

from core.errors import RuleViolation
from domain import rules
from domain.entities import EventDef, EventOption, Pet, Player, Week
from domain.enums import Category, EventMode

SICK_SLUG = "sick"
VACCINE_SLUG = "vaccine"


def blocked_slugs(player: Player, week_number: int) -> set[str]:
    """Прививка закрывает болезнь (и повторную прививку), пока не кончится срок."""
    if player.vaccinated_until >= week_number:
        return {SICK_SLUG, VACCINE_SLUG}
    return set()


def pick_event(
    defs: list[EventDef],
    week_number: int,
    seed: str,
    *,
    mode: EventMode = EventMode.RANDOM,
    blocked: set[str] | None = None,
) -> EventDef | None:
    """Взвешенный выбор по хешу, чтобы повторный запрос в тот же день дал то же событие."""
    skip = blocked or set()
    pool = [d for d in defs if d.min_week <= week_number and d.weight > 0 and d.slug not in skip]
    if not pool:
        return None
    if mode is EventMode.ESCALATING:
        weights = [d.weight * (d.min_week**2) for d in pool]
    else:
        weights = [d.weight for d in pool]
    total = sum(weights)
    point = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % total
    for definition, weight in zip(pool, weights, strict=True):
        point -= weight
        if point < 0:
            return definition
    return pool[-1]


@dataclass(frozen=True, slots=True)
class EventOutcome:
    coins_delta: int = 0
    xp_delta: int = 0
    need_changes: dict[Category, int] = field(default_factory=dict)
    spent: dict[Category, int] = field(default_factory=dict)
    note: str = ""
    unlock_shop: str | None = None


def apply_option(player: Player, pet: Pet, week: Week, option: EventOption) -> EventOutcome:
    effects = option.effects
    coins = int(effects.get("coins", 0) or 0)  # type: ignore[arg-type]
    if coins < 0 and player.free_coins < -coins:
        raise RuleViolation(f"Свободных монет только {player.free_coins}, а нужно {-coins}")

    spent: dict[Category, int] = {}
    for name, amount in dict(effects.get("cost", {}) or {}).items():  # type: ignore[arg-type]
        category = Category(name)
        if week.entry(category).left < int(amount):
            raise RuleViolation(f"В статье «{category}» не хватает {int(amount)} монет")
        spent[category] = int(amount)

    pay = int(effects.get("pay", 0) or 0)  # type: ignore[arg-type]
    coins_delta = coins
    if pay > 0:
        if player.free_coins + coins >= pay:
            coins_delta -= pay
        elif week.entry(Category.SAVE).left >= pay:
            spent[Category.SAVE] = spent.get(Category.SAVE, 0) + pay
        else:
            save_left = week.entry(Category.SAVE).left
            raise RuleViolation(
                f"Нужно {pay} монет: свободных {player.free_coins}, в копилке {save_left}"
            )

    if coins_delta < 0 and player.free_coins < -coins_delta:
        raise RuleViolation(f"Свободных монет только {player.free_coins}, а нужно {-coins_delta}")

    for category, amount in spent.items():
        week.entry(category).spent += amount

    player.free_coins += coins_delta
    changes: dict[Category, int] = {}
    for name, delta in dict(effects.get("need", {}) or {}).items():  # type: ignore[arg-type]
        category = Category(name)
        before = pet.needs[category]
        pet.needs[category] = max(0, min(rules.NEED_MAX, before + int(delta)))
        changes[category] = pet.needs[category] - before
    xp = int(effects.get("xp", 0) or 0)  # type: ignore[arg-type]
    pet.xp = max(0, pet.xp + xp)

    price_delta = dict(effects.get("price_delta") or {})
    if price_delta:
        merged = dict(week.modifiers.get("price_delta") or {})
        for name, delta in price_delta.items():
            merged[str(name)] = int(merged.get(str(name), 0)) + int(delta)
        week.modifiers = {**week.modifiers, "price_delta": merged}

    sale = effects.get("sale_percent")
    if sale:
        current = int(week.modifiers.get("sale_percent") or 0)
        week.modifiers = {**week.modifiers, "sale_percent": max(current, int(sale))}

    vaccinate = int(effects.get("vaccinate") or 0)  # type: ignore[arg-type]
    if vaccinate > 0:
        player.vaccinated_until = max(player.vaccinated_until, week.number + vaccinate - 1)

    unlock = effects.get("unlock_shop")
    unlock_slug = str(unlock) if unlock else None
    if unlock_slug and unlock_slug not in player.unlocked_shop:
        player.unlocked_shop = [*player.unlocked_shop, unlock_slug]

    return EventOutcome(
        coins_delta,
        xp,
        changes,
        spent,
        str(effects.get("note", "")),
        unlock_slug,
    )
