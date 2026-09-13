"""Лавка: витрина с доступностью по статье и покупка."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import NotFound
from domain.entities import LogEntry, Purchase, ShopItem
from domain.enums import ActionKind
from domain.services import shop as shop_rules


@dataclass(frozen=True, slots=True)
class ShelfItem:
    item: ShopItem
    left_in_category: int
    affordable: bool


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    outcome: shop_rules.PurchaseOutcome
    state: GameState


async def list_shelf(uow: UnitOfWork, player_id: UUID) -> list[ShelfItem]:
    async with uow:
        state = await load_state(uow, player_id)
        items = await uow.shop.list_items()
    return [
        ShelfItem(
            item,
            state.week.entry(item.category).left,
            state.week.entry(item.category).left >= item.cost,
        )
        for item in items
    ]


async def buy(uow: UnitOfWork, player_id: UUID, slug: str) -> PurchaseResult:
    async with uow:
        state = await load_state(uow, player_id)
        item = await uow.shop.get_item(slug)
        if item is None:
            raise NotFound("Такого товара нет в лавке")
        outcome = shop_rules.purchase(state.pet, state.week, item)
        await uow.shop.add_purchase(Purchase(uuid4(), player_id, state.week.id, slug, item.cost))
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.PURCHASE,
                amount=item.cost,
                category=item.category,
                note=f"Куплено: {item.name}",
                meta={"slug": slug, "sale": item.is_sale, "xp": item.xp_bonus},
            )
        )
        await uow.pets.save(state.pet)
        await uow.weeks.save(state.week)
        await uow.commit()
        return PurchaseResult(outcome, state)
