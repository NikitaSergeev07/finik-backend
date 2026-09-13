"""Схемы событий, достижений и профиля."""

from uuid import UUID

from pydantic import BaseModel

from api.schemas.game import StateOut
from application.use_cases.badges import BadgeView
from application.use_cases.events import ChoiceResult, EventView
from application.use_cases.profile import ProfileView
from domain.enums import Category


class EventOptionOut(BaseModel):
    key: str
    label: str


class EventOut(BaseModel):
    id: UUID
    slug: str
    title: str
    text: str
    day: int
    options: list[EventOptionOut]
    chosen: str | None

    @classmethod
    def from_view(cls, v: EventView) -> "EventOut":
        d, i = v.definition, v.instance
        return cls(
            id=i.id,
            slug=d.slug,
            title=d.title,
            text=d.text,
            day=i.day,
            options=[EventOptionOut(key=o.key, label=o.label) for o in d.options],
            chosen=i.chosen,
        )


class ChoiceIn(BaseModel):
    option: str


class ChoiceOut(BaseModel):
    note: str
    coins_delta: int
    xp_delta: int
    need_changes: dict[Category, int]
    spent: dict[Category, int]
    state: StateOut

    @classmethod
    def from_result(cls, r: ChoiceResult) -> "ChoiceOut":
        o = r.outcome
        return cls(
            note=o.note,
            coins_delta=o.coins_delta,
            xp_delta=o.xp_delta,
            need_changes=o.need_changes,
            spent=o.spent,
            state=StateOut.from_state(r.state),
        )


class BadgeOut(BaseModel):
    slug: str
    name: str
    note: str
    percent: int
    is_done: bool

    @classmethod
    def from_view(cls, v: BadgeView) -> "BadgeOut":
        return cls(
            slug=v.badge.slug,
            name=v.badge.name,
            note=v.badge.note,
            percent=v.percent,
            is_done=v.percent >= 100,
        )


class ProfileOut(BaseModel):
    earned_total: int
    saved_total: int
    weeks_done: int
    weekly_income: int
    sound_on: bool
    income_options: list[int]
    state: StateOut

    @classmethod
    def from_view(cls, v: ProfileView) -> "ProfileOut":
        from domain import rules

        return cls(
            earned_total=v.earned_total,
            saved_total=v.saved_total,
            weeks_done=v.weeks_done,
            weekly_income=v.state.player.weekly_income,
            sound_on=v.state.player.sound_on,
            income_options=list(rules.INCOME_OPTIONS),
            state=StateOut.from_state(v.state),
        )


class SettingsIn(BaseModel):
    weekly_income: int | None = None
    sound_on: bool | None = None
