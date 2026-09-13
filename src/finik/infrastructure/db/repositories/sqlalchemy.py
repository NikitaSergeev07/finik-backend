"""Репозитории поверх одной сессии. Сохранение обновляет поля найденной строки."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finik.domain.entities import Goal, LogEntry, Pet, Player, Week
from finik.infrastructure.db.models import GoalRow, PetRow, PlayerRow, WeekRow
from finik.infrastructure.db.repositories import mappers as m


class PlayerRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, player_id: UUID) -> Player | None:
        row = await self._s.get(PlayerRow, player_id)
        return m.player_from_row(row) if row else None

    async def get_by_device(self, device_id: str) -> Player | None:
        row = await self._s.scalar(select(PlayerRow).where(PlayerRow.device_id == device_id))
        return m.player_from_row(row) if row else None

    async def add(self, player: Player) -> None:
        self._s.add(m.player_to_row(player))

    async def save(self, player: Player) -> None:
        row = await self._s.get(PlayerRow, player.id)
        m.player_to_row(player, row)


class PetRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_player(self, player_id: UUID) -> Pet | None:
        row = await self._s.scalar(select(PetRow).where(PetRow.player_id == player_id))
        return m.pet_from_row(row) if row else None

    async def add(self, pet: Pet) -> None:
        self._s.add(m.pet_to_row(pet))

    async def save(self, pet: Pet) -> None:
        row = await self._s.get(PetRow, pet.id)
        m.pet_to_row(pet, row)


class WeekRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_current(self, player_id: UUID) -> Week | None:
        stmt = (
            select(WeekRow)
            .where(WeekRow.player_id == player_id, WeekRow.closed_at.is_(None))
            .order_by(WeekRow.number.desc())
            .limit(1)
        )
        row = await self._s.scalar(stmt)
        return m.week_from_row(row) if row else None

    async def list_closed(self, player_id: UUID, limit: int) -> list[Week]:
        stmt = (
            select(WeekRow)
            .where(WeekRow.player_id == player_id, WeekRow.closed_at.is_not(None))
            .order_by(WeekRow.number.desc())
            .limit(limit)
        )
        rows = (await self._s.scalars(stmt)).all()
        return [m.week_from_row(row) for row in reversed(rows)]

    async def add(self, week: Week) -> None:
        self._s.add(m.week_to_row(week))

    async def save(self, week: Week) -> None:
        row = await self._s.get(WeekRow, week.id)
        m.week_to_row(week, row)


class GoalRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_active(self, player_id: UUID) -> Goal | None:
        stmt = (
            select(GoalRow)
            .where(GoalRow.player_id == player_id, GoalRow.achieved_at.is_(None))
            .order_by(GoalRow.created_at.desc())
            .limit(1)
        )
        row = await self._s.scalar(stmt)
        return m.goal_from_row(row) if row else None

    async def add(self, goal: Goal) -> None:
        self._s.add(m.goal_to_row(goal))

    async def save(self, goal: Goal) -> None:
        row = await self._s.get(GoalRow, goal.id)
        m.goal_to_row(goal, row)


class LogRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, entry: LogEntry) -> None:
        self._s.add(m.log_to_row(entry))
