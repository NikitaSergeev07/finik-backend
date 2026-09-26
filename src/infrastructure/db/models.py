"""Таблицы. Игровые данные — по одной строке на сущность, справочники — контент."""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import ARRAY, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domain.enums import ActionKind, Category, Species, TaskKind, TaskTarget
from infrastructure.db.base import Base, IdMixin, TimestampMixin

from datetime import date
from sqlalchemy import Date, String, Text

class WordOfDayRow(Base):
    __tablename__ = "word_of_day"

    word_date: Mapped[date] = mapped_column(Date, primary_key=True)  # YYYY-MM-DD
    word: Mapped[str] = mapped_column(String(60))
    explanation: Mapped[str] = mapped_column(Text)


def enum_column(enum_type: type) -> Enum:
    # Храним имена (FINIK, FOOD), чтобы значения в базе совпадали с клиентом.
    return Enum(enum_type, name=enum_type.__name__.lower(), native_enum=False, length=24)


# --- игроки и питомцы -------------------------------------------------------

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    options: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    correct_option_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reward_coins: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    explanation: Mapped[str | None] = mapped_column(String(500), nullable=True)

class PlayerRow(IdMixin, TimestampMixin, Base):
    __tablename__ = "players"

    device_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    weekly_income: Mapped[int] = mapped_column(Integer, default=40)
    free_coins: Mapped[int] = mapped_column(Integer, default=0)
    sound_on: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (CheckConstraint("free_coins >= 0", name="free_coins_non_negative"),)


class PetRow(IdMixin, TimestampMixin, Base):
    __tablename__ = "pets"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(String(20))
    species: Mapped[Species] = mapped_column(enum_column(Species))
    xp: Mapped[int] = mapped_column(Integer, default=0)
    need_food: Mapped[int] = mapped_column(Integer)
    need_water: Mapped[int] = mapped_column(Integer)
    need_play: Mapped[int] = mapped_column(Integer)


# --- недели и план ----------------------------------------------------------


class WeekRow(IdMixin, TimestampMixin, Base):
    __tablename__ = "weeks"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    income: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer, default=1)
    overrun: Mapped[int] = mapped_column(Integer, default=0)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    entries: Mapped[list["PlanEntryRow"]] = relationship(
        back_populates="week", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (UniqueConstraint("player_id", "number", name="uq_weeks_player_number"),)


class PlanEntryRow(Base):
    __tablename__ = "plan_entries"

    week_id: Mapped[UUID] = mapped_column(
        ForeignKey("weeks.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[Category] = mapped_column(enum_column(Category), primary_key=True)
    planned: Mapped[int] = mapped_column(Integer, default=0)
    spent: Mapped[int] = mapped_column(Integer, default=0)

    week: Mapped[WeekRow] = relationship(back_populates="entries")

    __table_args__ = (CheckConstraint("planned >= 0 AND spent >= 0", name="amounts_non_negative"),)


# --- мечта и журнал ---------------------------------------------------------


class GoalRow(IdMixin, TimestampMixin, Base):
    __tablename__ = "goals"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(80))
    target: Mapped[int] = mapped_column(Integer)
    saved: Mapped[int] = mapped_column(Integer, default=0)
    achieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActionLogRow(IdMixin, Base):
    __tablename__ = "action_log"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    week_id: Mapped[UUID] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"), index=True)
    day: Mapped[int] = mapped_column(Integer)
    kind: Mapped[ActionKind] = mapped_column(enum_column(ActionKind))
    category: Mapped[Category | None] = mapped_column(enum_column(Category), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )


# --- контент: лавка, задания, уроки, достижения, события --------------------
# Заполняется сидом, не игроками. Прогресс игроков — в отдельных таблицах.


class ShopItemRow(Base):
    __tablename__ = "shop_items"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    category: Mapped[Category] = mapped_column(enum_column(Category))
    cost: Mapped[int] = mapped_column(Integer)
    old_cost: Mapped[int | None] = mapped_column(Integer)
    glyph: Mapped[str] = mapped_column(String(20))
    restore: Mapped[int] = mapped_column(Integer, default=0)
    xp_bonus: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PurchaseRow(IdMixin, Base):
    __tablename__ = "purchases"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    week_id: Mapped[UUID] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"))
    item_slug: Mapped[str] = mapped_column(ForeignKey("shop_items.slug"))
    cost: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )


class TaskDefRow(Base):
    __tablename__ = "task_defs"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(80))
    kind: Mapped[TaskKind] = mapped_column(enum_column(TaskKind))
    target: Mapped[TaskTarget | None] = mapped_column(enum_column(TaskTarget), nullable=True)
    reward: Mapped[int] = mapped_column(Integer)
    # Параметры правила выполнения: {"category": "FOOD"} для «уложись в план по еде» и т.п.
    params: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TaskProgressRow(IdMixin, Base):
    __tablename__ = "task_progress"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    week_id: Mapped[UUID] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"))
    task_slug: Mapped[str] = mapped_column(ForeignKey("task_defs.slug"))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    # Служебные данные правила: для урока — список отвеченных вопросов.
    data: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("player_id", "week_id", "task_slug", name="uq_task_progress_week"),
    )


class BadgeDefRow(Base):
    __tablename__ = "badge_defs"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    note: Mapped[str] = mapped_column(String(120))
    params: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class PlayerBadgeRow(Base):
    __tablename__ = "player_badges"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    badge_slug: Mapped[str] = mapped_column(ForeignKey("badge_defs.slug"), primary_key=True)
    percent: Mapped[int] = mapped_column(Integer, default=0)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EventDefRow(Base):
    __tablename__ = "event_defs"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    min_week: Mapped[int] = mapped_column(Integer, default=1)
    # Варианты выбора и последствия: [{"key": "pay", "label": "...", "effects": {...}}]
    options: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class EventInstanceRow(IdMixin, Base):
    __tablename__ = "event_instances"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    week_id: Mapped[UUID] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"))
    event_slug: Mapped[str] = mapped_column(ForeignKey("event_defs.slug"))
    day: Mapped[int] = mapped_column(Integer)
    chosen: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
