"""Единица работы: сессия открывается на сценарий, коммит явный, откат при исключении."""

from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.db.repositories.sqlalchemy import (
    BadgeRepo,
    EventRepo,
    GoalRepo,
    LogRepo,
    PetRepo,
    PlayerRepo,
    ShopRepo,
    TaskRepo,
    WeekRepo,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        s = self._session
        self.players = PlayerRepo(s)
        self.pets = PetRepo(s)
        self.weeks = WeekRepo(s)
        self.goals = GoalRepo(s)
        self.log = LogRepo(s)
        self.shop = ShopRepo(s)
        self.tasks = TaskRepo(s)
        self.events = EventRepo(s)
        self.badges = BadgeRepo(s)
        return self

    async def __aexit__(self, *exc: object) -> None:
        assert self._session is not None
        try:
            if exc[0] is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()
