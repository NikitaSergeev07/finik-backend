"""Цены лавки с множителем недели и скидкой события."""

from uuid import uuid4

from domain.entities import PlanEntry, ShopItem, Week
from domain.enums import Category
from domain.services import shop as shop_rules


def _item(cost: int = 12, old: int | None = None, hidden: bool = False) -> ShopItem:
    return ShopItem("food_week", "Корм", Category.FOOD, cost, old, "POT", 0, 0, hidden)


def _week(number: int = 1, **modifiers: object) -> Week:
    pid = uuid4()
    return Week(
        uuid4(),
        pid,
        number,
        40,
        day=1,
        entries={c: PlanEntry(c, 10) for c in Category},
        modifiers=dict(modifiers),
    )


def test_week_two_scales_food():
    priced = shop_rules.with_week_price(_item(), _week(2))
    assert priced.cost == 13


def test_price_rise_adds_two_to_food():
    week = _week(1, price_delta={"FOOD": 2})
    priced = shop_rules.with_week_price(_item(), week)
    assert priced.cost == 14


def test_sale_sets_old_cost():
    week = _week(1, sale_percent=50)
    priced = shop_rules.with_week_price(_item(cost=10), week)
    assert priced.cost == 9 and priced.old_cost == 10 and priced.is_sale


def test_hidden_until_unlocked():
    item = _item(hidden=True)
    assert not shop_rules.is_visible(item, [])
    assert shop_rules.is_visible(item, ["food_week"])


def test_small_sales_never_cut_more_than_ten_percent_even_for_cheap_items():
    from domain import rules

    for cost in range(1, 51):
        for number in (1, 2, 11, 20):
            item = ShopItem("x", "Товар", Category.FOOD, cost, None, "POT")
            week = _week(number)
            week.modifiers["sale_percent"] = 50  # Legacy/modifier input is clamped too.
            priced = shop_rules.with_week_price(item, week)
            base = rules.scaled_cost(cost, number)
            assert priced.cost * 100 >= base * 90
            assert priced.cost <= base
