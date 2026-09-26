
from pydantic import BaseModel, Field

class WordOfDayOut(BaseModel):
    word: str
    explanation: str
    date: str

class DiaryIn(BaseModel):
    events: list[str] | str = Field(
        ...,
        description="Список сообщений/событий за день или одна сконкатенированная строка",
    )


class DiaryOut(BaseModel):
    pet_name: str
    day: int
    entry: str

class DreamPlanIn(BaseModel):
    dream: str = Field(..., min_length=1, max_length=200, description="Описание мечты ребёнка (например, 'Хочу велосипед')")
    rules: str = Field(..., min_length=1, description="Правила игры или текущие финансовые условия")

class DreamPlanOut(BaseModel):
    plan: str = Field(..., description="Пошаговый план действий, сгенерированный ИИ")

class ChatMessageIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="Сообщение пользователя питомцу")

class ChatMessageOut(BaseModel):
    reply: str = Field(..., description="Ответ питомца")