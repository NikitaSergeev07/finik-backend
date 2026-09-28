"""Схемы ответов. Повторяют модели мобильного клиента, чтобы маппинг там был тривиальным."""

from dataclasses import asdict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from application.dto import CareResult, DayResult, GameState
from domain import rules
from domain.enums import Category, Mood, Species
from domain.services.persona import remark_fallback


class DeviceLoginIn(BaseModel):
    device_id: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    token: str
    has_pet: bool


class CreatePetIn(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    species: Species
    weekly_income: int
    goal_slug: str | None = None
    look_variant: int = Field(default=0, ge=0, le=2)


class GoalSelectIn(BaseModel):
    slug: str = Field(min_length=1, max_length=40)


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


class CustomizeIn(BaseModel):
    pot: str | None = Field(default=None, max_length=40)
    accessory: str | None = Field(default=None, max_length=40)
    look_variant: int | None = Field(default=None, ge=0, le=2)


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
    mood_note: str
    needs: list[NeedOut]
    look_variant: int = 0
    equipped_pot: str = ""
    equipped_accessory: str = ""


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
    plan_confirmed: bool = False


class GoalOut(BaseModel):
    id: UUID
    title: str
    target: int
    saved: int
    percent: int
    remain: int = 0
    catalog_slug: str = ""
    why: str = ""


class GoalCatalogOut(BaseModel):
    slug: str
    title: str
    target: int
    why: str


class CareActionOut(BaseModel):
    category: Category
    label: str
    cost: int


class StreakDayOut(BaseModel):
    label: str
    done: bool


class StreakOut(BaseModel):
    count: int
    goal: int
    bonus: int
    days: list[StreakDayOut]

    @classmethod
    def from_day(cls, day: int) -> "StreakOut":
        current = min(max(day, 1), rules.DAYS_IN_WEEK)
        days = [
            StreakDayOut(label=label, done=index + 1 <= current)
            for index, label in enumerate(rules.STREAK_LABELS)
        ]
        return cls(count=current, goal=rules.DAYS_IN_WEEK, bonus=rules.STREAK_BONUS, days=days)


class StateOut(BaseModel):
    free_coins: int
    weekly_income: int
    pet: PetOut
    week: WeekOut
    goal: GoalOut
    care_actions: list[CareActionOut]
    streak: StreakOut
    last_income: int = 0
    last_income_note: str = ""
    last_purchase_note: str = ""
    last_purchase_amount: int = 0
    owned_cosmetics: list[str] = Field(default_factory=list)

    @classmethod
    def from_state(cls, s: GameState) -> "StateOut":
        idx = s.pet.stage_index
        next_xp = rules.STAGE_THRESHOLDS[idx + 1] if idx + 1 < len(rules.STAGE_THRESHOLDS) else None
        option = next((g for g in rules.GOAL_CATALOG if g.slug == s.goal.catalog_slug), None)
        why = option.why if option else ""
        remain = max(0, s.goal.target - s.goal.saved)
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
                mood_note=remark_fallback(s.pet, s.week, s.goal),
                needs=[NeedOut(category=c, percent=v) for c, v in s.pet.needs.items()],
                look_variant=s.pet.look_variant,
                equipped_pot=s.pet.equipped_pot,
                equipped_accessory=s.pet.equipped_accessory,
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
                plan_confirmed=s.week.plan_confirmed,
            ),
            goal=GoalOut(
                id=s.goal.id,
                title=s.goal.title,
                target=s.goal.target,
                saved=s.goal.saved,
                percent=s.goal.percent,
                remain=remain,
                catalog_slug=s.goal.catalog_slug,
                why=why,
            ),
            care_actions=[
                CareActionOut(category=a.category, label=a.label, cost=a.cost)
                for a in rules.CARE_ACTIONS.values()
            ],
            streak=StreakOut.from_day(s.week.day),
            last_income=s.last_income or s.week.income,
            last_income_note=s.last_income_note or f"Пришёл доход {s.week.income}",
            last_purchase_note=s.last_purchase_note,
            last_purchase_amount=s.last_purchase_amount,
            owned_cosmetics=list(s.owned_cosmetics),
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
    interest: int = 0
    cashback: int = 0


class DayOut(BaseModel):
    day: int
    xp_gained: int
    week_finished: bool
    week_report: WeekReportOut | None
    state: StateOut
    wilted: bool = False
    wilt_xp_lost: int = 0

    @classmethod
    def from_result(cls, r: DayResult) -> "DayOut":
        report = WeekReportOut(**asdict(r.week)) if r.week else None
        return cls(
            day=r.day.day,
            xp_gained=r.day.xp_gained,
            week_finished=r.day.week_finished,
            week_report=report,
            state=StateOut.from_state(r.state),
            wilted=r.day.wilted,
            wilt_xp_lost=r.day.wilt_xp_lost,
        )
