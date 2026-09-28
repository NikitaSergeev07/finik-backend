from fastapi import APIRouter

from api.deps import PlayerIdDep, UowDep
from api.schemas.learning import ReviewAnswerIn, ReviewAnswerOut, ReviewOut
from application.use_cases import learning

router = APIRouter(prefix="/learning", tags=["Обучение"])


@router.get("/review", response_model=ReviewOut)
async def review(player_id: PlayerIdDep, uow: UowDep) -> ReviewOut:
    return ReviewOut.from_view(await learning.review(uow, player_id))


@router.post("/review/answer", response_model=ReviewAnswerOut)
async def answer_review(
    body: ReviewAnswerIn, player_id: PlayerIdDep, uow: UowDep
) -> ReviewAnswerOut:
    return ReviewAnswerOut.from_view(
        await learning.answer_review(uow, player_id, body.topic, body.answer_index)
    )
