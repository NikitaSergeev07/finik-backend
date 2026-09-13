"""Репозитории поверх одной сессии. Сохранение обновляет поля найденной строки."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import (
    Goal,
    LogEntry,
    Pet,
    Player,
    Purchase,
    QuizQuestion,
    ShopItem,
    TaskDef,
    TaskProgress,
    Week,
)
from domain.enums import ActionKind
from infrastructure.db.models import (
    ActionLogRow,
    GoalRow,
    PetRow,
    PlayerRow,
    PurchaseRow,
    QuizQuestionRow,
    ShopItemRow,
    TaskDefRow,
    TaskProgressRow,
    WeekRow,
)
from infrastructure.db.repositories import mappers as m


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

    async def care_days(self, player_id: UUID, week_id: UUID) -> int:
        stmt = select(func.count(func.distinct(ActionLogRow.day))).where(
            ActionLogRow.player_id == player_id,
            ActionLogRow.week_id == week_id,
            ActionLogRow.kind == ActionKind.CARE,
        )
        return int(await self._s.scalar(stmt) or 0)

    async def sum_amount(self, player_id: UUID, week_id: UUID, kind: ActionKind) -> int:
        stmt = select(func.coalesce(func.sum(ActionLogRow.amount), 0)).where(
            ActionLogRow.player_id == player_id,
            ActionLogRow.week_id == week_id,
            ActionLogRow.kind == kind,
        )
        return int(await self._s.scalar(stmt) or 0)


class ShopRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_items(self) -> list[ShopItem]:
        stmt = select(ShopItemRow).where(ShopItemRow.active.is_(True)).order_by(ShopItemRow.cost)
        return [m.shop_item_from_row(r) for r in (await self._s.scalars(stmt)).all()]

    async def get_item(self, slug: str) -> ShopItem | None:
        row = await self._s.get(ShopItemRow, slug)
        return m.shop_item_from_row(row) if row and row.active else None

    async def add_purchase(self, purchase: Purchase) -> None:
        self._s.add(m.purchase_to_row(purchase))

    async def count_discount_purchases(self, player_id: UUID, week_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(PurchaseRow)
            .join(ShopItemRow, ShopItemRow.slug == PurchaseRow.item_slug)
            .where(
                PurchaseRow.player_id == player_id,
                PurchaseRow.week_id == week_id,
                ShopItemRow.old_cost.is_not(None),
            )
        )
        return int(await self._s.scalar(stmt) or 0)


class TaskRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_defs(self) -> list[TaskDef]:
        stmt = select(TaskDefRow).where(TaskDefRow.active.is_(True)).order_by(TaskDefRow.slug)
        return [m.task_def_from_row(r) for r in (await self._s.scalars(stmt)).all()]

    async def get_def(self, slug: str) -> TaskDef | None:
        row = await self._s.get(TaskDefRow, slug)
        return m.task_def_from_row(row) if row and row.active else None

    async def list_questions(self, lesson_slug: str) -> list[QuizQuestion]:
        stmt = (
            select(QuizQuestionRow)
            .where(QuizQuestionRow.lesson_slug == lesson_slug)
            .order_by(QuizQuestionRow.order)
        )
        return [m.question_from_row(r) for r in (await self._s.scalars(stmt)).all()]

    async def get_progress(self, player_id: UUID, week_id: UUID, slug: str) -> TaskProgress | None:
        row = await self._progress_row(player_id, week_id, slug)
        return m.progress_from_row(row) if row else None

    async def upsert_progress(self, progress: TaskProgress) -> None:
        row = await self._progress_row(progress.player_id, progress.week_id, progress.task_slug)
        if row is None:
            self._s.add(m.progress_to_row(progress))
        else:
            m.progress_to_row(progress, row)

    async def _progress_row(
        self, player_id: UUID, week_id: UUID, slug: str
    ) -> TaskProgressRow | None:
        stmt = select(TaskProgressRow).where(
            TaskProgressRow.player_id == player_id,
            TaskProgressRow.week_id == week_id,
            TaskProgressRow.task_slug == slug,
        )
        return await self._s.scalar(stmt)
