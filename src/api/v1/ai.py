from fastapi import APIRouter, Query

from api.deps import LlmDep, PlayerIdDep, UowDep
from api.schemas.ai import (
    ChatIn,
    ChatOut,
    DreamPlanOut,
    OriginOut,
    QuizAnswerIn,
    QuizAnswerOut,
    QuizOut,
    RemarkOut,
    StoryOut,
    WordOut,
)
from application.use_cases import ai as use_ai

router = APIRouter(prefix="/ai", tags=["ИИ"])


@router.get("/remark", response_model=RemarkOut, summary="Реплика ростка")
async def remark(player_id: PlayerIdDep, uow: UowDep, llm: LlmDep) -> RemarkOut:
    """Короткая фраза по настроению и плану. Без модели — заготовка того же тона."""
    return RemarkOut.from_ai(await use_ai.remark(uow, llm, player_id))


@router.get("/week-summary", response_model=StoryOut, summary="Итог закрытой недели")
async def week_summary(player_id: PlayerIdDep, uow: UowDep, llm: LlmDep) -> StoryOut:
    """Текст для экрана истории. Пишется в неделю и больше не пересчитывается."""
    return StoryOut.from_ai(await use_ai.week_summary(uow, llm, player_id))


@router.get("/word-of-day", response_model=WordOut, summary="Слово дня")
async def word_of_day(player_id: PlayerIdDep, uow: UowDep, llm: LlmDep) -> WordOut:
    """Одно слово на календарный день. Все дети делят один вызов модели."""
    return WordOut.from_card(await use_ai.word_of_day(uow, llm, player_id))


@router.get("/diary", response_model=StoryOut, summary="Дневник ростка за сегодня")
async def diary(player_id: PlayerIdDep, uow: UowDep, llm: LlmDep) -> StoryOut:
    return StoryOut.from_ai(await use_ai.diary(uow, llm, player_id))


@router.get("/dream-plan", response_model=DreamPlanOut, summary="Разбить мечту на шаги")
async def dream_plan(player_id: PlayerIdDep, uow: UowDep, llm: LlmDep) -> DreamPlanOut:
    """Сроки и «на сколько раньше» считает сервер, модель пишет только совет."""
    return DreamPlanOut.from_view(await use_ai.dream_plan(uow, llm, player_id))


@router.get("/origin", response_model=OriginOut, summary="История ростка")
async def origin(player_id: PlayerIdDep, uow: UowDep, llm: LlmDep) -> OriginOut:
    """Три абзаца после знакомства. Кэш общий по имени и виду."""
    return OriginOut.from_ai(await use_ai.origin(uow, llm, player_id))


@router.get("/quiz", response_model=QuizOut, summary="Вопросы по ценам лавки")
async def quiz(
    player_id: PlayerIdDep,
    uow: UowDep,
    llm: LlmDep,
    kind: str = Query(default="quiz", pattern="^(quiz|riddle)$"),
) -> QuizOut:
    """Цифры и верный ответ считает сервер. kind=quiz или riddle."""
    return QuizOut.from_view(await use_ai.get_quiz(uow, llm, player_id, kind))


@router.post("/quiz/answer", response_model=QuizAnswerOut, summary="Ответ на вопрос лавки")
async def quiz_answer(body: QuizAnswerIn, player_id: PlayerIdDep, uow: UowDep) -> QuizAnswerOut:
    return QuizAnswerOut.from_view(
        await use_ai.answer_quiz(uow, player_id, body.index, body.answer_index, body.kind)
    )


@router.post("/chat", response_model=ChatOut, summary="Спросить ростка")
async def chat(body: ChatIn, player_id: PlayerIdDep, uow: UowDep, llm: LlmDep) -> ChatOut:
    """Стоплист на входе, лимит реплик на игровой день. Чужие темы мягко сворачиваются."""
    return ChatOut.from_ai(await use_ai.chat(uow, llm, player_id, body.text))
