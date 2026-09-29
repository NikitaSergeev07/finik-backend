"""События: выбор, надбавки цен, прививка, оплата без минуса."""

from uuid import uuid4

import pytest

from core.errors import RuleViolation
from domain import rules
from domain.entities import EventDef, EventOption, Pet, PlanEntry, Player, Week
from domain.enums import Category, EventMode, Species
from domain.services import events as event_rules


def _world(week_number: int = 1, coins: int = 10) -> tuple[Player, Pet, Week]:
    pid = uuid4()
    player = Player(pid, "dev", 40, free_coins=coins)
    pet = Pet(
        uuid4(),
        pid,
        "Кустик",
        Species.FINIK,
        xp=20,
        needs={c: rules.NEED_START for c in Category if c.is_need},
    )
    week = Week(
        uuid4(), pid, week_number, 40, day=1, entries={c: PlanEntry(c, 10) for c in Category}
    )
    return player, pet, week


def test_price_delta_stays_on_week():
    player, pet, week = _world()
    option = EventOption("ok", "Ок", {"price_delta": {"FOOD": 2}, "note": "дороже"})
    out = event_rules.apply_option(player, pet, week, option)
    assert week.modifiers["price_delta"]["FOOD"] == 2
    assert "дороже" in out.note


def test_sale_percent_on_week():
    player, pet, week = _world()
    event_rules.apply_option(player, pet, week, EventOption("look", "Смотрю", {"sale_percent": 30}))
    assert week.modifiers["sale_percent"] == 10


def test_pay_from_free_then_savings():
    player, pet, week = _world(coins=6)
    event_rules.apply_option(player, pet, week, EventOption("x", "x", {"pay": 5}))
    assert player.free_coins == 1
    player, pet, week = _world(coins=0)
    event_rules.apply_option(player, pet, week, EventOption("x", "x", {"pay": 5}))
    assert week.entry(Category.SAVE).spent == 5
    player, pet, week = _world(coins=0)
    week.entries[Category.SAVE] = PlanEntry(Category.SAVE, 2)
    with pytest.raises(RuleViolation):
        event_rules.apply_option(player, pet, week, EventOption("x", "x", {"pay": 5}))


def test_no_negative_coins():
    player, pet, week = _world(coins=3)
    with pytest.raises(RuleViolation):
        event_rules.apply_option(player, pet, week, EventOption("x", "x", {"coins": -8}))


def test_vaccinate_blocks_sick():
    player, pet, week = _world()
    event_rules.apply_option(player, pet, week, EventOption("p", "p", {"vaccinate": 4, "pay": 3}))
    assert player.vaccinated_until == 4
    blocked = event_rules.blocked_slugs(player, 1)
    assert "sick" in blocked and "vaccine" in blocked
    assert "sick" not in event_rules.blocked_slugs(player, 5)


def test_unlock_shop():
    player, pet, week = _world()
    event_rules.apply_option(
        player, pet, week, EventOption("l", "l", {"unlock_shop": "berry_treat"})
    )
    assert "berry_treat" in player.unlocked_shop


def test_escalating_prefers_later_events():
    defs = [
        EventDef("early", "Раннее", "", 5, 1, []),
        EventDef("late", "Позднее", "", 1, 4, []),
    ]
    picks = [
        event_rules.pick_event(defs, 4, f"seed-{i}", mode=EventMode.ESCALATING).slug
        for i in range(40)
    ]
    random_picks = [
        event_rules.pick_event(defs, 4, f"seed-{i}", mode=EventMode.RANDOM).slug for i in range(40)
    ]
    assert picks.count("late") > random_picks.count("late")
