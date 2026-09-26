from uuid import UUID
from pydantic import BaseModel, Field


class QuizQuestionOut(BaseModel):
    id: UUID = Field(description="ID вопроса (понадобится для проверки ответа)")
    question: str = Field(description="Текст вопроса")
    options: list[str] = Field(description="Список вариантов ответов")
    correct_option_index: int = Field(
        description="Индекс правильного ответа (0-based: 0 = первый вариант)"
    )
    reward_coins: int = Field(description="Количество монет за правильный ответ")
    explanation: str | None = Field(None, description="Обучающее пояснение к вопросу")