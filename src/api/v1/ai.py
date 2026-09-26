from fastapi import APIRouter, Depends
from api.deps import UowDep, SettingsDep, PlayerIdDep
from api.schemas.ai import WordOfDayOut
from application.use_cases import ai
from api.schemas.ai import DiaryIn, DiaryOut
from api.schemas.ai import DreamPlanIn, DreamPlanOut
from infrastructure.ai.deepseek import DeepSeekClient

router = APIRouter(prefix="/ai", tags=["ИИ"])

@router.get("/word-of-day", response_model=WordOfDayOut, summary="Слово дня от ИИ")
async def get_word_of_day(
    player_id: PlayerIdDep,
    uow: UowDep,
    settings: SettingsDep,
) -> WordOfDayOut:
    """Возвращает уникальное финансовое слово дня с детским объяснением.
    
    Слово одинаковое для всех пользователей и обновляется каждые сутки в 00:00 UTC.
    """
    ai_client = DeepSeekClient(settings)
    try:
        view = await ai.get_word_of_day(uow, ai_client)
        return WordOfDayOut(word=view.word, explanation=view.explanation, date=view.date)
    finally:
        await ai_client.aclose()

@router.post("/diary", response_model=DiaryOut, summary="Запись в дневник питомца по итогам дня")
async def generate_diary(
    body: DiaryIn,
    player_id: PlayerIdDep,
    uow: UowDep,
) -> DiaryOut:
    """Принимает список логов/сообщений за день (или единую строку) и генерирует

    от лица питомца запись в дневник с помощью DeepSeek.
    """
    view = await ai.generate_diary(uow, player_id, body.events)
    return DiaryOut(
        pet_name=view.pet_name,
        day=view.day,
        entry=view.entry,
    )

@router.post("/dream-plan", response_model=DreamPlanOut, summary="Построить план по мечте")
async def build_dream_plan(
    body: DreamPlanIn,
    player_id: PlayerIdDep,
    uow: UowDep,
) -> DreamPlanOut:
    """Принимает наименование мечты и правила игры,

    возвращает понятный пошаговый план действий от ИИ.
    """
    view = await ai.generate_dream_plan(
        uow=uow,
        player_id=player_id,
        dream=body.dream,
        rules=body.rules,
    )
    return DreamPlanOut(plan=view.plan)