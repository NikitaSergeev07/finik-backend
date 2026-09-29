from fastapi import APIRouter

from api.deps import PlayerIdDep, UowDep
from api.schemas.game import (
    CareIn,
    CareOut,
    CreatePetIn,
    CustomizeIn,
    DayOut,
    DemoAdvanceIn,
    DepositIn,
    GoalSelectIn,
    PlanIn,
    PlanTopUpIn,
    StateOut,
)
from application.use_cases import customize, gameplay, onboarding

router = APIRouter(tags=["Игра"])


@router.post("/pet", response_model=StateOut, status_code=201, summary="Создать сову")
async def create_pet(body: CreatePetIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    """Шаг знакомства: имя, вид и доход.

    Первая неделя начинается с пустого плана и полного дохода.
    """
    state = await onboarding.create_pet(
        uow,
        player_id,
        body.name,
        body.species,
        body.weekly_income,
        goal_slug=body.goal_slug,
        look_variant=body.look_variant,
        accessories=body.accessories,
    )
    return StateOut.from_state(state)


@router.get("/state", response_model=StateOut, summary="Состояние игры")
async def get_state(player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await gameplay.get_state(uow, player_id))


@router.post("/pet/customize", response_model=StateOut, summary="Надеть наряд")
async def customize_pet(body: CustomizeIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    """Наряды из магазина — только купленные.

    Шесть цветов и базовые аксессуары совы свободны. Пустая строка снимает наряд.
    """
    return StateOut.from_state(
        await customize.customize(
            uow,
            player_id,
            pot=body.pot,
            accessory=body.accessory,
            look_variant=body.look_variant,
            accessories=body.accessories,
        )
    )


@router.put("/plan", response_model=StateOut, summary="Распределить монеты по статьям")
async def set_plan(body: PlanIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await gameplay.set_plan(uow, player_id, body.as_domain()))


@router.post("/plan/confirm", response_model=StateOut, summary="Утвердить план недели")
async def confirm_plan(player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    """После утверждения можно только добавлять свободные монеты в статьи."""
    return StateOut.from_state(await gameplay.confirm_plan(uow, player_id))


@router.post("/care", response_model=CareOut, summary="Напоить, покормить или поиграть")
async def care(body: CareIn, player_id: PlayerIdDep, uow: UowDep) -> CareOut:
    return CareOut.from_result(await gameplay.care_for_pet(uow, player_id, body.category))


@router.put("/goal", response_model=StateOut, summary="Выбрать мечту из каталога")
async def select_goal(body: GoalSelectIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await onboarding.select_goal(uow, player_id, body.slug))


@router.post(
    "/goal/deposit", response_model=StateOut, summary="Перевести из копилки недели в выбранную цель"
)
async def deposit(body: DepositIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await gameplay.deposit(uow, player_id, body.amount))


@router.post("/day/end", response_model=DayOut, summary="Завершить игровой день")
async def end_day(player_id: PlayerIdDep, uow: UowDep) -> DayOut:
    """Только демо: перейти к следующему местному дню. В понедельник закрывается неделя."""
    return DayOut.from_result(await gameplay.end_day(uow, player_id))


@router.post("/plan/topup", response_model=StateOut, summary="Пополнить статьи свободными монетами")
async def topup(body: PlanTopUpIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await gameplay.topup_plan(uow, player_id, body.as_domain()))


@router.post("/goal/withdraw", response_model=StateOut, summary="Снять накопления в развлечения")
async def withdraw(body: DepositIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await gameplay.withdraw(uow, player_id, body.amount))


@router.post("/demo/advance", response_model=StateOut, summary="Пропустить время только в демо")
async def advance(body: DemoAdvanceIn, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(
        await gameplay.advance_demo(uow, player_id, days=body.days, to_week_end=body.to_week_end)
    )
