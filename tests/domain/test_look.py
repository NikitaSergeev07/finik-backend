"""Наряды: купить из игр, надеть только своё, без минуса монет."""

from uuid import uuid4

import pytest

from core.errors import RuleViolation
from domain.entities import Pet, PlanEntry, ShopItem, Week
from domain.enums import Category, Species
from domain.services import look as look_rules
from domain.services import shop as shop_rules


def _pet() -> Pet:
    return Pet(
        uuid4(),
        uuid4(),
        "Кустик",
        Species.CACTUS,
        xp=0,
        needs={c: 70 for c in Category if c.is_need},
    )


def _item(slug: str, slot: str, name: str = "Наряд") -> ShopItem:
    return ShopItem(slug, name, Category.PLAY, 3, None, "POT", 0, 0, slot=slot)


def test_equip_requires_owned():
    pet = _pet()
    catalog = {"pot_blue": _item("pot_blue", "pot", "Синий горшок")}
    with pytest.raises(RuleViolation, match="Сначала купи"):
        look_rules.apply_customize(pet, set(), catalog, pot="pot_blue")


def test_equip_and_unequip_pot():
    pet = _pet()
    catalog = {"pot_blue": _item("pot_blue", "pot", "Синий горшок")}
    look_rules.apply_customize(pet, {"pot_blue"}, catalog, pot="pot_blue")
    assert pet.equipped_pot == "pot_blue"
    look_rules.apply_customize(pet, {"pot_blue"}, catalog, pot="")
    assert pet.equipped_pot == ""


def test_wrong_slot_rejected():
    pet = _pet()
    catalog = {"pot_blue": _item("pot_blue", "pot")}
    with pytest.raises(RuleViolation, match="аксессуар"):
        look_rules.apply_customize(pet, {"pot_blue"}, catalog, accessory="pot_blue")


def test_look_variant_has_six_colors():
    pet = _pet()
    look_rules.apply_customize(pet, set(), {}, look_variant=2)
    assert pet.look_variant == 2
    with pytest.raises(RuleViolation):
        look_rules.apply_customize(pet, set(), {}, look_variant=6)


def test_cosmetic_purchase_spends_play_not_food():
    pid = uuid4()
    pet = _pet()
    week = Week(
        uuid4(),
        pid,
        1,
        40,
        day=1,
        entries={c: PlanEntry(c, 10) for c in Category},
    )
    item = _item("scarf_knit", "accessory", "Шарфик")
    shop_rules.purchase(pet, week, item)
    assert week.entry(Category.PLAY).spent == 3
    assert week.entry(Category.FOOD).spent == 0
    assert pet.needs[Category.FOOD] == 70
