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
    PARENT_BONUS = "PARENT_BONUS"


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
