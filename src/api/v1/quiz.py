"""Compatibility route for the daily quiz from the AI branch."""

from fastapi import APIRouter

from api.deps import LlmDep, PlayerIdDep, UowDep
from api.schemas.ai import QuizOut
from application.use_cases import ai as use_ai

router = APIRouter(prefix="/quiz", tags=["Викторина"])


@router.get("/daily", response_model=QuizOut, summary="Вопросы дня")
async def daily_quiz(player_id: PlayerIdDep, uow: UowDep, llm: LlmDep) -> QuizOut:
    """Return stable daily questions without exposing answers before submission."""
    return QuizOut.from_view(await use_ai.get_quiz(uow, llm, player_id))
