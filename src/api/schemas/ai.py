
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