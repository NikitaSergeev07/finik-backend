from fastapi import APIRouter

from api.deps import PlayerIdDep, UowDep
from api.schemas.game import (
    CareIn,
    CareOut,
    CreatePetIn,
    DayOut,
    DepositIn,
    PlanIn,
    StateOut,
)
from application.use_cases import gameplay, onboarding

router = APIRouter(tags=["Игра"])


@router.post("/pet", response_model=StateOut, status_code=201, summary="Создать ростка")
async def create_pet(body: CreatePetIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    """Шаг знакомства: имя, вид и доход.

    Первая неделя сразу распределяется по совету 40/30/10/20.
    """
    state = await onboarding.create_pet(uow, player_id, body.name, body.species, body.weekly_income)
    return StateOut.from_state(state)


@router.get("/state", response_model=StateOut, summary="Состояние игры")
async def get_state(player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await gameplay.get_state(uow, player_id))


@router.put("/plan", response_model=StateOut, summary="Распределить монеты по статьям")
async def set_plan(body: PlanIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await gameplay.set_plan(uow, player_id, body.as_domain()))


@router.post("/care", response_model=CareOut, summary="Полить, покормить или поиграть")
async def care(body: CareIn, player_id: PlayerIdDep, uow: UowDep) -> CareOut:
    return CareOut.from_result(await gameplay.care_for_pet(uow, player_id, body.category))


@router.post("/goal/deposit", response_model=StateOut, summary="Отложить свободные монеты в мечту")
async def deposit(body: DepositIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await gameplay.deposit(uow, player_id, body.amount))


@router.post("/day/end", response_model=DayOut, summary="Завершить игровой день")
async def end_day(player_id: PlayerIdDep, uow: UowDep) -> DayOut:
    """Потребности убывают, начисляется опыт. На седьмом дне закрывается неделя и приходит доход."""
    return DayOut.from_result(await gameplay.end_day(uow, player_id))
