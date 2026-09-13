from fastapi import APIRouter

from api.deps import PlayerIdDep, UowDep
from api.schemas.content import HistoryOut
from application.use_cases import history

router = APIRouter(prefix="/weeks", tags=["История"])


@router.get("/history", response_model=HistoryOut, summary="Закрытые недели и отчёт последней")
async def week_history(player_id: PlayerIdDep, uow: UowDep) -> HistoryOut:
    """Столбики «Что откладывал» на экране мечты и таблица план/факт для отчёта недели."""
    return HistoryOut.from_weeks(await history.closed_weeks(uow, player_id))
