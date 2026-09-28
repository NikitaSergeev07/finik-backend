"""Течение времени: конец дня и закрытие недели."""

from dataclasses import dataclass

from domain import rules
from domain.entities import Goal, Pet, Player, Week
from domain.enums import Category


@dataclass(frozen=True, slots=True)
class DayOutcome:
    day: int
    xp_gained: int
    week_finished: bool
    wilted: bool = False
    wilt_xp_lost: int = 0


@dataclass(frozen=True, slots=True)
class WeekOutcome:
    number: int
    saved: int
    overrun: int
    returned_coins: int
    xp_gained: int
    goal_achieved: bool
    interest: int = 0
    cashback: int = 0


def end_day(pet: Pet, week: Week) -> DayOutcome:
    for category in rules.DAILY_DECAY:
        pet.needs[category] = max(0, pet.needs[category] - rules.decay_for(pet.species, category))
    xp = rules.XP_GOOD_DAY if all(value > 50 for value in pet.needs.values()) else 0
    pet.xp += xp
    wilted = any(value == 0 for value in pet.needs.values())
    wilt_lost = 0
    if wilted:
        before = pet.xp
        pet.xp = rules.wilt_xp(pet.xp)
        wilt_lost = before - pet.xp
        xp -= wilt_lost
    week.day += 1
    return DayOutcome(week.day, xp, week.day > rules.DAYS_IN_WEEK, wilted, wilt_lost)


def close_week(player: Player, pet: Pet, week: Week, goal: Goal) -> WeekOutcome:
    """Копилка уходит в мечту с процентами, остатки статей возвращаются, опыт за дисциплину.

    Проценты: 5% от остатка статьи SAVE (копилка недели), дробь отбрасывается.
    Редкий вид получает крошечный кэшбэк с остатка своей бонусной статьи — до возврата монет.
    """
    leftover_save = week.entry(Category.SAVE).left
    interest = rules.savings_interest(leftover_save)
    goal.saved += leftover_save + interest
    week.entry(Category.SAVE).spent += leftover_save

    cashback = 0
    trait = rules.SPECIES_TRAITS[pet.species]
    if trait.rare:
        cashback = rules.cashback_coins(week.entry(trait.bonus_category).left)

    # Остатки статей возвращаются монетами; факт трат не трогаем, он нужен отчёту план/факт.
    returned = sum(week.entry(cat).left for cat in Category if cat.is_need)
    player.free_coins += returned + cashback

    xp = leftover_save * rules.XP_PER_SAVED_COIN
    xp += rules.XP_WEEK_NO_OVERRUN if week.overrun == 0 else -rules.XP_OVERRUN_PENALTY
    pet.xp = max(0, pet.xp + xp)

    achieved = goal.saved >= goal.target and goal.achieved_at is None
    return WeekOutcome(
        week.number,
        leftover_save,
        week.overrun,
        returned,
        xp,
        achieved,
        interest,
        cashback,
    )
