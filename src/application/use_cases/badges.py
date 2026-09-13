"""Достижения: проценты считаются на лету и запоминаются для родительского кабинета."""

from dataclasses import dataclass
from uuid import UUID

from application.ports import UnitOfWork
from application.use_cases._common import load_state
from domain.entities import Badge
from domain.services import badges as badge_rules


@dataclass(frozen=True, slots=True)
class BadgeView:
    badge: Badge
    percent: int


async def list_badges(uow: UnitOfWork, player_id: UUID) -> list[BadgeView]:
    async with uow:
        state = await load_state(uow, player_id)
        facts = badge_rules.BadgeFacts(
            closed_weeks=await uow.weeks.list_closed(player_id, limit=52),
            pet=state.pet,
            goal=state.goal,
            discount_purchases_total=await uow.shop.count_discount_purchases_total(player_id),
        )
        views = []
        for badge in await uow.badges.list_defs():
            percent = badge_rules.percent_for(badge, facts)
            await uow.badges.upsert_progress(player_id, badge.slug, percent)
            views.append(BadgeView(badge, percent))
        await uow.commit()
        return views
