"""Течение времени: конец дня и закрытие недели."""

from dataclasses import dataclass

from finik.domain import rules
from finik.domain.entities import Goal, Pet, Player, Week
from finik.domain.enums import Category


@dataclass(frozen=True, slots=True)
class DayOutcome:
    day: int
    xp_gained: int
    week_finished: bool


@dataclass(frozen=True, slots=True)
class WeekOutcome:
    number: int
    saved: int
    overrun: int
    returned_coins: int
    xp_gained: int
    goal_achieved: bool


def end_day(pet: Pet, week: Week) -> DayOutcome:
    for category in rules.DAILY_DECAY:
        pet.needs[category] = max(0, pet.needs[category] - rules.decay_for(pet.species, category))
    xp = rules.XP_GOOD_DAY if all(value > 50 for value in pet.needs.values()) else 0
    pet.xp += xp
    week.day += 1
    return DayOutcome(week.day, xp, week_finished=week.day > rules.DAYS_IN_WEEK)


def close_week(player: Player, pet: Pet, week: Week, goal: Goal) -> WeekOutcome:
    """Копилка уходит в мечту, остатки статей возвращаются, опыт за дисциплину."""
    saved = week.entry(Category.SAVE).left
    goal.saved += saved
    week.entry(Category.SAVE).spent += saved

    returned = sum(week.entry(cat).left for cat in Category if cat.is_need)
    for category in Category:
        if category.is_need:
            week.entry(category).spent = week.entry(category).planned
    player.free_coins += returned

    xp = saved * rules.XP_PER_SAVED_COIN
    xp += rules.XP_WEEK_NO_OVERRUN if week.overrun == 0 else -rules.XP_OVERRUN_PENALTY
    pet.xp = max(0, pet.xp + xp)

    achieved = goal.saved >= goal.target and goal.achieved_at is None
    return WeekOutcome(week.number, saved, week.overrun, returned, xp, achieved)
