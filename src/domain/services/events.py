"""События дня: детерминированный выбор и применение последствий выбранного варианта."""

import hashlib
from dataclasses import dataclass, field

from core.errors import RuleViolation
from domain import rules
from domain.entities import EventDef, EventOption, Pet, Player, Week
from domain.enums import Category


def pick_event(defs: list[EventDef], week_number: int, seed: str) -> EventDef | None:
    """Взвешенный выбор по хешу, чтобы повторный запрос в тот же день дал то же событие."""
    pool = [d for d in defs if d.min_week <= week_number and d.weight > 0]
    if not pool:
        return None
    total = sum(d.weight for d in pool)
    point = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % total
    for d in pool:
        point -= d.weight
        if point < 0:
            return d
    return pool[-1]


@dataclass(frozen=True, slots=True)
class EventOutcome:
    coins_delta: int = 0
    xp_delta: int = 0
    need_changes: dict[Category, int] = field(default_factory=dict)
    spent: dict[Category, int] = field(default_factory=dict)
    note: str = ""


def apply_option(player: Player, pet: Pet, week: Week, option: EventOption) -> EventOutcome:
    effects = option.effects
    coins = int(effects.get("coins", 0))  # type: ignore[arg-type]
    if coins < 0 and player.free_coins < -coins:
        raise RuleViolation(f"Свободных монет только {player.free_coins}, а нужно {-coins}")

    spent: dict[Category, int] = {}
    for name, amount in dict(effects.get("cost", {})).items():  # type: ignore[arg-type]
        category = Category(name)
        if week.entry(category).left < int(amount):
            raise RuleViolation(f"В статье «{category}» не хватает {int(amount)} монет")
        spent[category] = int(amount)
    for category, amount in spent.items():
        week.entry(category).spent += amount

    player.free_coins += coins
    changes: dict[Category, int] = {}
    for name, delta in dict(effects.get("need", {})).items():  # type: ignore[arg-type]
        category = Category(name)
        before = pet.needs[category]
        pet.needs[category] = max(0, min(rules.NEED_MAX, before + int(delta)))
        changes[category] = pet.needs[category] - before
    xp = int(effects.get("xp", 0))  # type: ignore[arg-type]
    pet.xp = max(0, pet.xp + xp)
    return EventOutcome(coins, xp, changes, spent, str(effects.get("note", "")))
