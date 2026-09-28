"""Ответы ИИ. source: llm — свежий ответ модели, cache — повтор, fallback — заготовка."""

from pydantic import BaseModel, Field

from application.use_cases.ai import (
    AiText,
    DreamPlanView,
    QuizAnswerView,
    QuizView,
    WordCard,
)
from domain.enums import Mood


class RemarkOut(BaseModel):
    text: str
    mood: Mood
    source: str

    @classmethod
    def from_ai(cls, item: AiText) -> "RemarkOut":
        assert item.mood is not None
        return cls(text=item.text, mood=item.mood, source=item.source)


class StoryOut(BaseModel):
    text: str
    source: str
    week_number: int | None = None

    @classmethod
    def from_ai(cls, item: AiText) -> "StoryOut":
        return cls(text=item.text, source=item.source, week_number=item.week_number)


class WordOut(BaseModel):
    word: str
    meaning: str
    example: str
    source: str

    @classmethod
    def from_card(cls, card: WordCard) -> "WordOut":
        return cls(word=card.word, meaning=card.meaning, example=card.example, source=card.source)


class DreamStepOut(BaseModel):
    title: str
    coins: int


class DreamPlanOut(BaseModel):
    title: str
    remain: int
    weekly_save: int
    weeks_left: int
    steps: list[DreamStepOut]
    advice: str
    source: str
    cut_play: int = 0
    faster_save: int = 0
    weeks_saved: int = 0

    @classmethod
    def from_view(cls, view: DreamPlanView) -> "DreamPlanOut":
        return cls(
            title=view.title,
            remain=view.remain,
            weekly_save=view.weekly_save,
            weeks_left=view.weeks_left,
            steps=[DreamStepOut(title=title, coins=coins) for title, coins in view.steps],
            advice=view.advice,
            source=view.source,
            cut_play=view.cut_play,
            faster_save=view.faster_save,
            weeks_saved=view.weeks_saved,
        )


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class ChatOut(BaseModel):
    text: str
    source: str
    blocked: bool
    chat_left: int | None = None

    @classmethod
    def from_ai(cls, item: AiText) -> "ChatOut":
        return cls(
            text=item.text,
            source=item.source,
            blocked=item.blocked,
            chat_left=item.chat_left,
        )


class OriginOut(BaseModel):
    text: str
    source: str

    @classmethod
    def from_ai(cls, item: AiText) -> "OriginOut":
        return cls(text=item.text, source=item.source)


class QuizQuestionOut(BaseModel):
    index: int
    question: str
    options: list[str]


class QuizOut(BaseModel):
    kind: str
    source: str
    rewarded: bool
    questions: list[QuizQuestionOut]

    @classmethod
    def from_view(cls, view: QuizView) -> "QuizOut":
        return cls(
            kind=view.kind,
            source=view.source,
            rewarded=view.rewarded,
            questions=[
                QuizQuestionOut(index=q.index, question=q.question, options=q.options)
                for q in view.questions
            ],
        )


class QuizAnswerIn(BaseModel):
    index: int = Field(ge=0, le=5)
    answer_index: int = Field(ge=0, le=5)
    kind: str = "quiz"


class QuizAnswerOut(BaseModel):
    correct: bool
    explanation: str
    coins: int
    rewarded: bool

    @classmethod
    def from_view(cls, view: QuizAnswerView) -> "QuizAnswerOut":
        return cls(
            correct=view.correct,
            explanation=view.explanation,
            coins=view.coins,
            rewarded=view.rewarded,
        )
