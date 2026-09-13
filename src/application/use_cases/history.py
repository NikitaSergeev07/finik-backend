"""История закрытых недель для экрана «Мечта» и отчёт последней недели."""

from uuid import UUID

from application.ports import UnitOfWork
from application.use_cases._common import load_state
from domain.entities import Week


async def closed_weeks(uow: UnitOfWork, player_id: UUID, limit: int = 8) -> list[Week]:
    async with uow:
        await load_state(uow, player_id)
        return await uow.weeks.list_closed(player_id, limit)
