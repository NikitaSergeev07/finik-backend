from fastapi import APIRouter

from api.deps import LlmDep, PlayerIdDep, UowDep
from api.schemas.content import AnswerIn, AnswerOut, QuestionOut, TaskOut
from api.schemas.game import StateOut
from api.schemas.learning import HintIn, HintOut
from application.use_cases import learning, tasks

router = APIRouter(prefix="/tasks", tags=["Задания"])


@router.get("", response_model=list[TaskOut], summary="Задания недели с прогрессом")
async def list_tasks(player_id: PlayerIdDep, uow: UowDep) -> list[TaskOut]:
    return [TaskOut.from_view(v) for v in await tasks.list_tasks(uow, player_id)]


@router.get("/{slug}/questions", response_model=list[QuestionOut], summary="Вопросы мини-урока")
async def questions(slug: str, player_id: PlayerIdDep, uow: UowDep) -> list[QuestionOut]:
    """Правильный ответ клиенту не отдаётся, он проверяется на сервере."""
    return [QuestionOut.from_entity(q) for q in await tasks.list_questions(uow, player_id, slug)]


@router.post("/{slug}/answer", response_model=AnswerOut, summary="Ответить на вопрос урока")
async def answer_question(
    slug: str, body: AnswerIn, player_id: PlayerIdDep, uow: UowDep
) -> AnswerOut:
    result = await tasks.answer(
        uow,
        player_id,
        slug,
        body.question_slug,
        body.answer_index,
        body.answer_value,
    )
    return AnswerOut.from_result(result)


@router.post("/{slug}/claim", response_model=StateOut, summary="Забрать награду за задание")
async def claim(slug: str, player_id: PlayerIdDep, uow: UowDep) -> StateOut:
    return StateOut.from_state(await tasks.claim(uow, player_id, slug))


@router.post("/{slug}/hint", response_model=HintOut, summary="Подсказка после ошибки")
async def lesson_hint(
    slug: str, body: HintIn, player_id: PlayerIdDep, uow: UowDep, llm: LlmDep
) -> HintOut:
    return HintOut.from_view(await learning.hint(uow, llm, player_id, slug, body.question_slug))
