"""Подсказки и короткое повторение навыков."""

from datetime import date

from pydantic import BaseModel, Field

from application.use_cases.learning import HintView, ReviewAnswerView, ReviewView


class HintIn(BaseModel):
    question_slug: str = Field(min_length=1, max_length=80)


class HintOut(BaseModel):
    text: str
    source: str

    @classmethod
    def from_view(cls, view: HintView) -> "HintOut":
        return cls(text=view.text, source=view.source)


class ReviewOut(BaseModel):
    topic: str | None
    title: str
    question: str
    options: list[str]
    next_due: date | None

    @classmethod
    def from_view(cls, view: ReviewView) -> "ReviewOut":
        return cls(
            topic=view.topic,
            title=view.title,
            question=view.question,
            options=list(view.options),
            next_due=view.next_due,
        )


class ReviewAnswerIn(BaseModel):
    topic: str
    answer_index: int = Field(ge=0, le=5)


class ReviewAnswerOut(BaseModel):
    correct: bool
    explanation: str
    next_due: date | None

    @classmethod
    def from_view(cls, view: ReviewAnswerView) -> "ReviewAnswerOut":
        return cls(
            correct=view.correct,
            explanation=view.explanation,
            next_due=view.next_due,
        )
