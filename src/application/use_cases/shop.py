"""Лавка: витрина с доступностью по статье и покупка. Цены — с множителем недели."""

from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import NotFound, RuleViolation
from domain.entities import LogEntry, Purchase, ShopItem
from domain.enums import ActionKind
from domain.services import look as look_rules
from domain.services import shop as shop_rules


@dataclass(frozen=True, slots=True)
class ShelfItem:
    item: ShopItem
    left_in_category: int
    affordable: bool
    owned: bool = False
    equipped: bool = False


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    outcome: shop_rules.PurchaseOutcome
    state: GameState


def _priced(uow_items: list[ShopItem], state: GameState) -> list[ShopItem]:
    unlocked = state.player.unlocked_shop
    visible = [item for item in uow_items if shop_rules.is_visible(item, unlocked)]
    return [shop_rules.with_week_price(item, state.week) for item in visible]


async def list_shelf(uow: UnitOfWork, player_id: UUID) -> list[ShelfItem]:
    async with uow:
        state = await load_state(uow, player_id)
        items = _priced(await uow.shop.list_items(), state)
        owned = set(state.owned_cosmetics)
        wearing = {state.pet.equipped_pot, state.pet.equipped_accessory}
    return [
        ShelfItem(
            item,
            state.week.entry(item.category).left,
            state.week.entry(item.category).left >= item.cost,
            item.slug in owned,
            item.slug in wearing,
        )
        for item in items
    ]


async def buy(uow: UnitOfWork, player_id: UUID, slug: str) -> PurchaseResult:
    async with uow:
        state = await load_state(uow, player_id)
        item = await uow.shop.get_item(slug)
        if item is None or not shop_rules.is_visible(item, state.player.unlocked_shop):
            raise NotFound("Такого товара нет в лавке")
        priced = shop_rules.with_week_price(item, state.week)
        if priced.slot and priced.slug in state.owned_cosmetics:
            raise RuleViolation(f"«{priced.name}» уже у тебя. Надень его кнопкой «Надеть».")
        outcome = shop_rules.purchase(state.pet, state.week, priced)
        await uow.shop.add_purchase(Purchase(uuid4(), player_id, state.week.id, slug, priced.cost))
        if priced.slot == look_rules.POT:
            state.pet.equipped_pot = priced.slug
        elif priced.slot == look_rules.ACCESSORY:
            state.pet.equipped_accessory = priced.slug
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.PURCHASE,
                amount=priced.cost,
                category=priced.category,
                note=f"Куплено: {priced.name}",
                meta={"slug": slug, "sale": priced.is_sale, "xp": priced.xp_bonus},
            )
        )
        await uow.pets.save(state.pet)
        await uow.weeks.save(state.week)
        await uow.commit()
        owned = state.owned_cosmetics
        if priced.slot and priced.slug not in owned:
            owned = (*owned, priced.slug)
        hinted = replace(
            state,
            last_purchase_note=f"Куплено: {priced.name}",
            last_purchase_amount=priced.cost,
            owned_cosmetics=owned,
        )
        return PurchaseResult(outcome, hinted)
