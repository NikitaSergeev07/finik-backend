"""Репозитории поверх одной сессии. Сохранение обновляет поля найденной строки."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import (
    Badge,
    EventDef,
    EventInstance,
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
from domain.enums import ActionKind, Category
from infrastructure.db.models import (
    ActionLogRow,
    AiCacheRow,
    BadgeDefRow,
    EventDefRow,
    EventInstanceRow,
    GoalRow,
    PetRow,
    PlayerBadgeRow,
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
        # Serialize every player command, including lazy calendar catch-up.
        row = await self._s.scalar(
            select(PlayerRow).where(PlayerRow.id == player_id).with_for_update()
        )
        return m.player_from_row(row) if row else None

    async def get_by_device(self, device_id: str) -> Player | None:
        await self._s.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": device_id}
        )
        row = await self._s.scalar(select(PlayerRow).where(PlayerRow.device_id == device_id))
        return m.player_from_row(row) if row else None

    async def add(self, player: Player) -> None:
        self._s.add(m.player_to_row(player))

    async def save(self, player: Player) -> None:
        row = await self._s.get(PlayerRow, player.id)
        m.player_to_row(player, row)

    async def wipe_progress(self, player_id: UUID) -> None:
        # Журнал, покупки, прогресс и события уходят каскадом вслед за неделями и питомцем.
        for model in (WeekRow, PetRow, GoalRow, PlayerBadgeRow, AiCacheRow):
            await self._s.execute(delete(model).where(model.player_id == player_id))


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
        await self._s.flush()

    async def save(self, week: Week) -> None:
        row = await self._s.get(WeekRow, week.id)
        m.week_to_row(week, row)


class GoalRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_active(self, player_id: UUID) -> Goal | None:
        stmt = (
            select(GoalRow)
            .join(PlayerRow, PlayerRow.id == GoalRow.player_id)
            .where(
                GoalRow.player_id == player_id, GoalRow.catalog_slug == PlayerRow.selected_goal_slug
            )
            .order_by(GoalRow.created_at.desc())
            .limit(1)
        )
        row = await self._s.scalar(stmt)
        return m.goal_from_row(row) if row else None

    async def list_all(self, player_id: UUID) -> list[Goal]:
        rows = await self._s.scalars(select(GoalRow).where(GoalRow.player_id == player_id))
        return [m.goal_from_row(row) for row in rows]

    async def add(self, goal: Goal) -> None:
        self._s.add(m.goal_to_row(goal))

    async def save(self, goal: Goal) -> None:
        row = await self._s.get(GoalRow, goal.id)
        m.goal_to_row(goal, row)


class LogRepo:
    async def earned_total(self, player_id: UUID) -> int:
        kinds = (
            ActionKind.INCOME,
            ActionKind.TASK_REWARD,
            ActionKind.STREAK,
            ActionKind.PARENT_BONUS,
            ActionKind.EVENT_CHOICE,
            ActionKind.INTEREST,
            ActionKind.CASHBACK,
        )
        stmt = select(func.coalesce(func.sum(ActionLogRow.amount), 0)).where(
            ActionLogRow.player_id == player_id,
            ActionLogRow.kind.in_(kinds),
            ActionLogRow.amount > 0,
        )
        return int(await self._s.scalar(stmt) or 0)

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

    async def list_day(self, player_id: UUID, week_id: UUID, day: int) -> list[LogEntry]:
        stmt = (
            select(ActionLogRow)
            .where(
                ActionLogRow.player_id == player_id,
                ActionLogRow.week_id == week_id,
                ActionLogRow.day == day,
            )
            .order_by(ActionLogRow.created_at)
        )
        return [m.log_from_row(row) for row in (await self._s.scalars(stmt)).all()]

    async def latest(self, player_id: UUID, kind: ActionKind) -> LogEntry | None:
        stmt = (
            select(ActionLogRow)
            .where(ActionLogRow.player_id == player_id, ActionLogRow.kind == kind)
            .order_by(ActionLogRow.created_at.desc())
            .limit(1)
        )
        row = await self._s.scalar(stmt)
        return m.log_from_row(row) if row else None


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
        return await self._count_discount(player_id, week_id)

    async def count_discount_purchases_total(self, player_id: UUID) -> int:
        return await self._count_discount(player_id, None)

    async def count_need_purchases(self, player_id: UUID, week_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(PurchaseRow)
            .join(ShopItemRow, ShopItemRow.slug == PurchaseRow.item_slug)
            .where(
                PurchaseRow.player_id == player_id,
                PurchaseRow.week_id == week_id,
                ShopItemRow.category.in_((Category.FOOD, Category.WATER)),
            )
        )
        return int(await self._s.scalar(stmt) or 0)

    async def list_owned_slugs(self, player_id: UUID) -> list[str]:
        stmt = (
            select(PurchaseRow.item_slug)
            .join(ShopItemRow, ShopItemRow.slug == PurchaseRow.item_slug)
            .where(PurchaseRow.player_id == player_id, ShopItemRow.slot != "")
            .distinct()
        )
        return list((await self._s.scalars(stmt)).all())

    async def _count_discount(self, player_id: UUID, week_id: UUID | None) -> int:
        stmt = (
            select(func.count())
            .select_from(PurchaseRow)
            .join(ShopItemRow, ShopItemRow.slug == PurchaseRow.item_slug)
            .where(PurchaseRow.player_id == player_id, ShopItemRow.old_cost.is_not(None))
        )
        if week_id is not None:
            stmt = stmt.where(PurchaseRow.week_id == week_id)
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

    async def count_rewarded(self, player_id: UUID) -> int:
        stmt = select(func.count()).where(
            TaskProgressRow.player_id == player_id,
            TaskProgressRow.rewarded_at.is_not(None),
        )
        return int(await self._s.scalar(stmt) or 0)

    async def _progress_row(
        self, player_id: UUID, week_id: UUID, slug: str
    ) -> TaskProgressRow | None:
        stmt = select(TaskProgressRow).where(
            TaskProgressRow.player_id == player_id,
            TaskProgressRow.week_id == week_id,
            TaskProgressRow.task_slug == slug,
        )
        return await self._s.scalar(stmt)


class EventRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_defs(self) -> list[EventDef]:
        stmt = select(EventDefRow).where(EventDefRow.active.is_(True)).order_by(EventDefRow.slug)
        return [m.event_def_from_row(r) for r in (await self._s.scalars(stmt)).all()]

    async def get_def(self, slug: str) -> EventDef | None:
        row = await self._s.get(EventDefRow, slug)
        return m.event_def_from_row(row) if row and row.active else None

    async def get_for_day(self, player_id: UUID, week_id: UUID, day: int) -> EventInstance | None:
        stmt = select(EventInstanceRow).where(
            EventInstanceRow.player_id == player_id,
            EventInstanceRow.week_id == week_id,
            EventInstanceRow.day == day,
        )
        row = await self._s.scalar(stmt)
        return m.event_from_row(row) if row else None

    async def get(self, instance_id: UUID) -> EventInstance | None:
        row = await self._s.get(EventInstanceRow, instance_id)
        return m.event_from_row(row) if row else None

    async def add(self, instance: EventInstance) -> None:
        self._s.add(m.event_to_row(instance))

    async def save(self, instance: EventInstance) -> None:
        row = await self._s.get(EventInstanceRow, instance.id)
        m.event_to_row(instance, row)


class BadgeRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_defs(self) -> list[Badge]:
        rows = (await self._s.scalars(select(BadgeDefRow).order_by(BadgeDefRow.slug))).all()
        return [m.badge_from_row(r) for r in rows]

    async def upsert_progress(self, player_id: UUID, slug: str, percent: int) -> None:
        row = await self._s.get(PlayerBadgeRow, (player_id, slug))
        if row is None:
            row = PlayerBadgeRow(player_id=player_id, badge_slug=slug)
            self._s.add(row)
        row.percent = percent
        if percent >= 100 and row.unlocked_at is None:
            row.unlocked_at = datetime.now(UTC)


class AiCacheRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, key: str) -> str | None:
        row = await self._s.get(AiCacheRow, key)
        return row.payload if row else None

    async def put(self, key: str, payload: str, *, player_id: UUID | None, kind: str) -> None:
        row = await self._s.get(AiCacheRow, key)
        if row is None:
            self._s.add(AiCacheRow(key=key, player_id=player_id, kind=kind, payload=payload))
            return
        row.payload = payload
        row.kind = kind
        row.player_id = player_id
