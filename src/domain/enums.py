"""Перечисления домена. Значения совпадают с моделями мобильного клиента (core/model)."""

from enum import StrEnum


class Species(StrEnum):
    """Вид ростка. Черта меняет скорость убывания потребностей и бонус к опыту."""

    FINIK = "FINIK"  # пальма, пьёт много воды, +опыт за воду
    CACTUS = "CACTUS"  # кактус, редко ест, дешёвый уход
    SPARK = "SPARK"  # огонёк, скучает быстрее, +опыт за игры


class Category(StrEnum):
    """Статьи недельного плана. Три потребности плюс копилка."""

    FOOD = "FOOD"
    WATER = "WATER"
    PLAY = "PLAY"
    SAVE = "SAVE"

    @property
    def is_need(self) -> bool:
        return self is not Category.SAVE


class Mood(StrEnum):
    HAPPY = "HAPPY"
    OKAY = "OKAY"
    BORED = "BORED"
    SAD = "SAD"


class EventMode(StrEnum):
    """Как выбирается событие дня: взвешенный хеш или уклон в более поздние истории."""

    RANDOM = "random"
    ESCALATING = "escalating"


class ActionKind(StrEnum):
    """Что записывается в журнал: основа отчётов, летописи и достижений."""

    CARE = "CARE"
    PURCHASE = "PURCHASE"
    DEPOSIT = "DEPOSIT"
    OVERRUN = "OVERRUN"
    TASK_REWARD = "TASK_REWARD"
    EVENT_CHOICE = "EVENT_CHOICE"
    DAY_END = "DAY_END"
    WEEK_CLOSE = "WEEK_CLOSE"
    STREAK = "STREAK"
    PARENT_BONUS = "PARENT_BONUS"
    INTEREST = "INTEREST"
    CASHBACK = "CASHBACK"
    WILT = "WILT"
    INCOME = "INCOME"
    PLAN_CONFIRM = "PLAN_CONFIRM"


class TaskKind(StrEnum):
    LESSON = "LESSON"
    WEEK = "WEEK"
    HABIT = "HABIT"
    DAY = "DAY"


class TaskTarget(StrEnum):
    QUIZ = "QUIZ"
    PLAN = "PLAN"
    GOAL = "GOAL"
    SHOP = "SHOP"
