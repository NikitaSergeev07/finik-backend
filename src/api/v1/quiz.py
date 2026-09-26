from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from api.deps import UowDep
from infrastructure.db.models import QuizQuestion
from infrastructure.ai.llm.deepseek import generate_daily_quiz_question

router = APIRouter(prefix="/quiz", tags=["Викторина"])


@router.get("/daily")
async def get_daily_quiz(uow: UowDep):
    async with uow:
        # 1. Пробуем получить случайный вопрос из БД
        stmt = select(QuizQuestion).order_by(func.random()).limit(1)
        result = await uow._session.execute(stmt)
        question = result.scalars().first()

        # 2. Если в БД нет вопросов, генерируем через DeepSeek "на лету"
        if not question:
            try:
                generated_data = await generate_daily_quiz_question()

                question = QuizQuestion(
                    question=generated_data["question"],
                    options=generated_data["options"],
                    correct_option_index=generated_data["correct_option_index"],
                    reward_coins=generated_data.get("reward_coins", 10),
                    explanation=generated_data.get("explanation"),
                )
                uow._session.add(question)
                await uow._session.commit()
                await uow._session.refresh(question)

            except Exception as e:
                await uow._session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Ошибка генерации вопроса через LLM: {str(e)}",
                )

        return {
            "id": question.id,
            "question": question.question,
            "options": question.options,
            "correct_option_index": question.correct_option_index,
            "reward_coins": question.reward_coins,
            "explanation": question.explanation,
        }