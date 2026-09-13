"""Сущности домена. Чистые данные без привязки к базе и HTTP."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from finik.domain import rules
from finik.domain.enums import ActionKind, Category, Mood, Species


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
