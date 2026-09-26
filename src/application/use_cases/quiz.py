from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import select, func

from application.ports import UnitOfWork
from infrastructure.db.models import QuizQuestion


@dataclass(slots=True)
class QuizQuestionView:
    id: UUID
    question: str
    options: list[str]
    correct_option_index: int
    reward_coins: int
    explanation: str | None


async def get_daily_quiz(uow: UnitOfWork) -> QuizQuestionView | None:
    async with uow:
        stmt = select(QuizQuestion).order_by(func.random()).limit(1)
        result = await uow._session.execute(stmt)
        quiz = result.scalar_one_or_none()

        if not quiz:
            return None

        return QuizQuestionView(
            id=quiz.id,
            question=quiz.question,
            options=quiz.options,
            correct_option_index=quiz.correct_option_index,
            reward_coins=quiz.reward_coins,
            explanation=quiz.explanation,
        )