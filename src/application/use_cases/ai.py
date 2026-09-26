from datetime import UTC, datetime
from dataclasses import dataclass
from application.ports import UnitOfWork
from uuid import UUID
from core.config import get_settings
from application.use_cases._common import load_state
from infrastructure.ai.deepseek import DeepSeekClient

@dataclass(frozen=True, slots=True)
class WordOfDayView:
    word: str
    explanation: str
    date: str

async def get_word_of_day(uow: UnitOfWork, ai_client: DeepSeekClient) -> WordOfDayView:
    today = datetime.now(UTC).date()

    async with uow:
        # 1. Ищем слово на сегодня в базе
        existing = await uow.word_of_day.get_by_date(today)
        if existing:
            return WordOfDayView(
                word=existing.word,
                explanation=existing.explanation,
                date=today.isoformat(),
            )

        # 2. Если нет — генерируем через DeepSeek
        word, explanation = await ai_client.generate_word_of_day()

        # 3. Сохраняем в БД для всех остальных запросов на сегодня
        saved = await uow.word_of_day.add(today, word, explanation)
        await uow.commit()

        return WordOfDayView(
            word=saved.word,
            explanation=saved.explanation,
            date=today.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class DiaryView:
    pet_name: str
    day: int
    entry: str


async def generate_diary(
    uow: UnitOfWork,
    player_id: UUID,
    events: list[str] | str,
) -> DiaryView:
    async with uow:
        # Загружаем текущее состояние, чтобы получить имя и вид питомца, а также текущий день
        state = await load_state(uow, player_id)
        pet_name = state.pet.name
        species_name = state.pet.species.value
        day = state.week.day

    # Запрос к LLM выносим за пределы транзакции БД
    ai_client = DeepSeekClient(get_settings())
    try:
        entry_text = await ai_client.generate_pet_diary(
            pet_name=pet_name,
            species_name=species_name,
            day_number=day,
            events=events,
        )
        return DiaryView(pet_name=pet_name, day=day, entry=entry_text)
    finally:
        await ai_client.aclose()