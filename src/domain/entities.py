"""Сущности домена. Чистые данные без привязки к базе и HTTP."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from domain import rules
from domain.enums import ActionKind, Category, Mood, Species, TaskKind, TaskTarget


@dataclass(slots=True)
class Player:
    id: UUID
    device_id: str
    weekly_income: int
    free_coins: int
    sound_on: bool = True


@dataclass(slots=True)
class Pet:
    id: UUID
    player_id: UUID
    name: str
    species: Species
    xp: int
    needs: dict[Category, int]

    @property
    def stage_index(self) -> int:
        return rules.stage_for_xp(self.xp)

    @property
    def stage_name(self) -> str:
        return rules.STAGE_NAMES[self.stage_index]

    @property
    def mood(self) -> Mood:
        return rules.mood_for_needs(list(self.needs.values()))


@dataclass(slots=True)
class PlanEntry:
    category: Category
    planned: int
    spent: int = 0

    @property
    def left(self) -> int:
        return self.planned - self.spent


@dataclass(slots=True)
class Week:
    id: UUID
    player_id: UUID
    number: int
    income: int
    day: int
    entries: dict[Category, PlanEntry]
    overrun: int = 0
    closed_at: datetime | None = None

    @property
    def planned_total(self) -> int:
        return sum(entry.planned for entry in self.entries.values())

    def entry(self, category: Category) -> PlanEntry:
        return self.entries[category]

    def entry_saved(self) -> int:
        """Сколько монет ушло в мечту из копилки этой недели."""
        return self.entries[Category.SAVE].spent


@dataclass(slots=True)
class Goal:
    id: UUID
    player_id: UUID
    title: str
    target: int
    saved: int
    achieved_at: datetime | None = None

    @property
    def percent(self) -> int:
        return round(self.saved * 100 / self.target) if self.target else 0


@dataclass(slots=True)
class LogEntry:
    """Строка журнала. Пишется при каждом значимом действии."""

    player_id: UUID
    week_id: UUID
    day: int
    kind: ActionKind
    amount: int = 0
    category: Category | None = None
    note: str = ""
    meta: dict[str, object] = field(default_factory=dict)


# --- контент и прогресс по нему ------------------------------------------


@dataclass(slots=True)
class ShopItem:
    slug: str
    name: str
    category: Category
    cost: int
    old_cost: int | None
    glyph: str
    restore: int = 0
    xp_bonus: int = 0

    @property
    def is_sale(self) -> bool:
        return self.old_cost is not None

    @property
    def sale_percent(self) -> int:
        return round((1 - self.cost / self.old_cost) * 100) if self.old_cost else 0


@dataclass(slots=True)
class Purchase:
    id: UUID
    player_id: UUID
    week_id: UUID
    item_slug: str
    cost: int


@dataclass(slots=True)
class TaskDef:
    slug: str
    title: str
    kind: TaskKind
    target: TaskTarget | None
    reward: int
    params: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class TaskProgress:
    player_id: UUID
    week_id: UUID
    task_slug: str
    progress: int = 0
    data: dict[str, object] = field(default_factory=dict)
    done_at: datetime | None = None
    rewarded_at: datetime | None = None


@dataclass(slots=True)
class QuizQuestion:
    slug: str
    lesson_slug: str
    order: int
    question: str
    options: list[str]
    right_index: int
    explanation: str


@dataclass(slots=True)
class Badge:
    slug: str
    name: str
    note: str
    params: dict[str, object] = field(default_factory=dict)


# --- события -----------------------------------------------------------------


@dataclass(slots=True)
class EventOption:
    key: str
    label: str
    effects: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class EventDef:
    slug: str
    title: str
    text: str
    weight: int
    min_week: int
    options: list[EventOption]

    def option(self, key: str) -> EventOption | None:
        return next((o for o in self.options if o.key == key), None)


@dataclass(slots=True)
class EventInstance:
    id: UUID
    player_id: UUID
    week_id: UUID
    event_slug: str
    day: int
    chosen: str | None = None
    resolved_at: datetime | None = None
