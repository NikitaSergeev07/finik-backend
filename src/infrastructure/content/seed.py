"""Заполнение справочников. Идемпотентно: повторный запуск обновляет строки, не плодя дублей.

Запуск: make seed
"""

import asyncio

from sqlalchemy.dialects.postgresql import insert

from infrastructure.content import catalog
from infrastructure.db.engine import get_session_factory
from infrastructure.db.models import (
    BadgeDefRow,
    EventDefRow,
    QuizQuestionRow,
    ShopItemRow,
    TaskDefRow,
)

_TABLES = [
    (ShopItemRow, catalog.SHOP_ITEMS, ["slug"]),
    (TaskDefRow, catalog.TASK_DEFS, ["slug"]),
    (QuizQuestionRow, catalog.QUIZ_QUESTIONS, ["slug"]),
    (BadgeDefRow, catalog.BADGE_DEFS, ["slug"]),
    (EventDefRow, catalog.EVENT_DEFS, ["slug"]),
]


async def seed() -> dict[str, int]:
    counts: dict[str, int] = {}
    async with get_session_factory()() as session:
        for model, rows, keys in _TABLES:
            stmt = insert(model).values(rows)
            update_cols = {c: stmt.excluded[c] for c in rows[0] if c not in keys}
            await session.execute(stmt.on_conflict_do_update(index_elements=keys, set_=update_cols))
            counts[model.__tablename__] = len(rows)
        await session.commit()
    return counts


if __name__ == "__main__":
    for table, count in asyncio.run(seed()).items():
        print(f"{table}: {count}")
