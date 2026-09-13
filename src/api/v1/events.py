from uuid import UUID

from fastapi import APIRouter

from api.deps import PlayerIdDep, UowDep
from api.schemas.social import ChoiceIn, ChoiceOut, EventOut
from application.use_cases import events

router = APIRouter(prefix="/events", tags=["События"])


@router.get("/today", response_model=EventOut | None, summary="Событие дня")
async def today(player_id: PlayerIdDep, uow: UowDep) -> EventOut | None:
    """Одно событие на игровой день. Повторный запрос возвращает то же самое."""
    view = await events.today(uow, player_id)
    return EventOut.from_view(view) if view else None


@router.post("/{event_id}/choose", response_model=ChoiceOut, summary="Сделать выбор")
async def choose(event_id: UUID, body: ChoiceIn, player_id: PlayerIdDep, uow: UowDep) -> ChoiceOut:
    """Последствия применяются один раз. В ответе объяснение, что произошло и почему."""
    return ChoiceOut.from_result(await events.choose(uow, player_id, event_id, body.option))
