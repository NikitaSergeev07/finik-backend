"""Схемы лавки, заданий и истории недель."""

from pydantic import BaseModel, Field

from api.schemas.game import StateOut
from application.use_cases.history import Week
from application.use_cases.shop import PurchaseResult, ShelfItem
from application.use_cases.tasks import AnswerResult, TaskView
from domain.entities import QuizQuestion
from domain.enums import Category, TaskKind, TaskTarget


class TermOut(BaseModel):
    word: str
    meaning: str
    example: str


class ShopItemOut(BaseModel):
    slug: str
    name: str
    category: Category
    cost: int
    old_cost: int | None
    sale_percent: int
    glyph: str
    left_in_category: int
    affordable: bool
    restore: int = 0
    xp_bonus: int = 0
    kind: str = "NEED"
    slot: str = ""
    owned: bool = False
    equipped: bool = False

    @classmethod
    def from_shelf(cls, s: ShelfItem) -> "ShopItemOut":
        i = s.item
        return cls(
            slug=i.slug,
            name=i.name,
            category=i.category,
            cost=i.cost,
            old_cost=i.old_cost,
            sale_percent=i.sale_percent,
            glyph=i.glyph,
            left_in_category=s.left_in_category,
            affordable=s.affordable,
            restore=i.restore,
            xp_bonus=i.xp_bonus,
            kind=i.kind,
            slot=i.slot,
            owned=s.owned,
            equipped=s.equipped,
        )


class BuyIn(BaseModel):
    slug: str


class PurchaseOut(BaseModel):
    slug: str
    name: str
    cost: int
    restored: int
    xp_gained: int
    state: StateOut

    @classmethod
    def from_result(cls, r: PurchaseResult) -> "PurchaseOut":
        o = r.outcome
        return cls(
            slug=o.item.slug,
            name=o.item.name,
            cost=o.item.cost,
            restored=o.restored,
            xp_gained=o.xp_gained,
            state=StateOut.from_state(r.state),
        )


class TaskOut(BaseModel):
    slug: str
    title: str
    subtitle: str
    kind: TaskKind
    target: TaskTarget | None
    reward: int
    progress: int
    goal: int
    done: bool
    rewarded: bool
    activity: str = "QUIZ"

    @classmethod
    def from_view(cls, v: TaskView) -> "TaskOut":
        t, s = v.task, v.status
        return cls(
            slug=t.slug,
            title=t.title,
            subtitle=s.subtitle,
            kind=t.kind,
            target=t.target,
            reward=t.reward,
            progress=s.progress,
            goal=s.goal,
            done=s.done,
            rewarded=v.rewarded,
            activity="ADVENTURE" if t.params.get("adventure") else "QUIZ",
        )


class QuestionOut(BaseModel):
    slug: str
    order: int
    question: str
    options: list[str]
    activity: str = "CHOICE"
    scene: str = ""

    @classmethod
    def from_entity(cls, q: QuizQuestion) -> "QuestionOut":
        return cls(
            slug=q.slug,
            order=q.order,
            question=q.question,
            options=q.options,
            activity=q.activity,
            scene=q.scene,
        )


class AnswerIn(BaseModel):
    question_slug: str
    answer_index: int | None = Field(default=None, ge=0, le=5)
    answer_value: int | None = Field(default=None, ge=0, le=100)


class AnswerOut(BaseModel):
    correct: bool
    explanation: str
    lesson_done: bool
    answered: int
    total: int

    @classmethod
    def from_result(cls, r: AnswerResult) -> "AnswerOut":
        return cls(
            correct=r.correct,
            explanation=r.explanation,
            lesson_done=r.lesson_done,
            answered=r.answered,
            total=r.total,
        )


class HistoryWeekOut(BaseModel):
    number: int
    saved: int
    overrun: int
    income: int
    tone: str


class ReportRowOut(BaseModel):
    category: Category
    planned: int
    actual: int
    is_over: bool


class HistoryOut(BaseModel):
    weeks: list[HistoryWeekOut]
    last_report: list[ReportRowOut]
    last_summary: str
    last_story: str | None = None
    last_income: int = 0
    last_purchase_note: str = ""

    @classmethod
    def from_weeks(cls, weeks: list[Week]) -> "HistoryOut":
        out = []
        for w in weeks:
            saved = w.entry(Category.SAVE).spent
            share = saved * 100 // w.income if w.income else 0
            tone = (
                "BAD" if w.overrun else "HIGH" if share >= 20 else "MID" if share >= 10 else "LOW"
            )
            out.append(
                HistoryWeekOut(
                    number=w.number, saved=saved, overrun=w.overrun, income=w.income, tone=tone
                )
            )
        rows, summary, story = [], "", None
        if weeks:
            last = weeks[-1]
            rows = [
                ReportRowOut(
                    category=e.category,
                    planned=e.planned,
                    actual=e.spent,
                    is_over=e.spent > e.planned,
                )
                for e in last.entries.values()
            ]
            spent = sum(e.spent for e in last.entries.values() if e.category.is_need)
            summary = (
                f"Доход {last.income} · потрачено {spent} · "
                f"отложено {last.entry(Category.SAVE).spent}"
            )
            story = last.summary_text
        last_income = weeks[-1].income if weeks else 0
        return cls(
            weeks=out,
            last_report=rows,
            last_summary=summary,
            last_story=story,
            last_income=last_income,
        )
