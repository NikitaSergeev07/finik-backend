"""Схемы ответов. Повторяют модели мобильного клиента, чтобы маппинг там был тривиальным."""

from dataclasses import asdict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from finik.application.dto import CareResult, DayResult, GameState
from finik.domain import rules
from finik.domain.enums import Category, Mood, Species


class DeviceLoginIn(BaseModel):
    device_id: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    token: str
    has_pet: bool


class CreatePetIn(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    species: Species
    weekly_income: int


class PlanIn(BaseModel):
    food: int = Field(ge=0)
    water: int = Field(ge=0)
    play: int = Field(ge=0)
    save: int = Field(ge=0)

    def as_domain(self) -> dict[Category, int]:
        return {
            Category.FOOD: self.food,
            Category.WATER: self.water,
            Category.PLAY: self.play,
            Category.SAVE: self.save,
        }


class CareIn(BaseModel):
    category: Category


class DepositIn(BaseModel):
    amount: int = Field(gt=0)


class NeedOut(BaseModel):
    category: Category
    percent: int


class PetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    species: Species
    xp: int
    stage_index: int
    stage_name: str
    next_stage_xp: int | None
    mood: Mood
    needs: list[NeedOut]


class PlanEntryOut(BaseModel):
    category: Category
    planned: int
    spent: int
    left: int


class WeekOut(BaseModel):
    id: UUID
    number: int
    day: int
    income: int
    overrun: int
    entries: list[PlanEntryOut]


class GoalOut(BaseModel):
    id: UUID
    title: str
    target: int
    saved: int
    percent: int


class CareActionOut(BaseModel):
    category: Category
    label: str
    cost: int


class StateOut(BaseModel):
    free_coins: int
    weekly_income: int
    pet: PetOut
    week: WeekOut
    goal: GoalOut
    care_actions: list[CareActionOut]

    @classmethod
    def from_state(cls, s: GameState) -> "StateOut":
        idx = s.pet.stage_index
        next_xp = rules.STAGE_THRESHOLDS[idx + 1] if idx + 1 < len(rules.STAGE_THRESHOLDS) else None
        return cls(
            free_coins=s.player.free_coins,
            weekly_income=s.player.weekly_income,
            pet=PetOut(
                id=s.pet.id,
                name=s.pet.name,
                species=s.pet.species,
                xp=s.pet.xp,
                stage_index=idx,
                stage_name=s.pet.stage_name,
                next_stage_xp=next_xp,
                mood=s.pet.mood,
                needs=[NeedOut(category=c, percent=v) for c, v in s.pet.needs.items()],
            ),
            week=WeekOut(
                id=s.week.id,
                number=s.week.number,
                day=s.week.day,
                income=s.week.income,
                overrun=s.week.overrun,
                entries=[
                    PlanEntryOut(category=e.category, planned=e.planned, spent=e.spent, left=e.left)
                    for e in s.week.entries.values()
                ],
            ),
            goal=GoalOut(
                id=s.goal.id,
                title=s.goal.title,
                target=s.goal.target,
                saved=s.goal.saved,
                percent=s.goal.percent,
            ),
            care_actions=[
                CareActionOut(category=a.category, label=a.label, cost=a.cost)
                for a in rules.CARE_ACTIONS.values()
            ],
        )


class CareOut(BaseModel):
    category: Category
    cost: int
    restored: int
    xp_gained: int
    from_savings: bool
    state: StateOut

    @classmethod
    def from_result(cls, r: CareResult) -> "CareOut":
        o = r.outcome
        return cls(
            category=o.category,
            cost=o.cost,
            restored=o.restored,
            xp_gained=o.xp_gained,
            from_savings=o.from_savings,
            state=StateOut.from_state(r.state),
        )


class WeekReportOut(BaseModel):
    number: int
    saved: int
    overrun: int
    returned_coins: int
    xp_gained: int
    goal_achieved: bool


class DayOut(BaseModel):
    day: int
    xp_gained: int
    week_finished: bool
    week_report: WeekReportOut | None
    state: StateOut

    @classmethod
    def from_result(cls, r: DayResult) -> "DayOut":
        report = WeekReportOut(**asdict(r.week)) if r.week else None
        return cls(
            day=r.day.day,
            xp_gained=r.day.xp_gained,
            week_finished=r.day.week_finished,
            week_report=report,
            state=StateOut.from_state(r.state),
        )
