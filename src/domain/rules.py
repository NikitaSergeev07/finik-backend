"""Числа и правила игры в одном месте. Менять баланс — здесь, а не по коду."""

from dataclasses import dataclass

from domain.enums import Category, Mood, Species

DAYS_IN_WEEK = 7
INCOME_OPTIONS: tuple[int, ...] = (20, 40, 60)
NEED_MAX = 100
NEED_START = 70

# Совет по распределению дохода, который мобилка показывает кнопкой «Совет 40/30/10/20».
ADVICE_SHARES: dict[Category, int] = {
    Category.FOOD: 40,
    Category.WATER: 30,
    Category.PLAY: 10,
    Category.SAVE: 20,
}


@dataclass(frozen=True, slots=True)
class CareAction:
    category: Category
    label: str
    cost: int
    restore: int


CARE_ACTIONS: dict[Category, CareAction] = {
    Category.WATER: CareAction(Category.WATER, "Полить", cost=2, restore=30),
    Category.FOOD: CareAction(Category.FOOD, "Покормить", cost=3, restore=30),
    Category.PLAY: CareAction(Category.PLAY, "Поиграть", cost=2, restore=30),
}

# Сколько потребность теряет за игровой день до учёта черты ростка.
DAILY_DECAY: dict[Category, int] = {
    Category.WATER: 15,
    Category.FOOD: 12,
    Category.PLAY: 18,
}


@dataclass(frozen=True, slots=True)
class SpeciesTrait:
    """Множители убывания потребностей и статья, за которую росток даёт бонусный опыт."""

    decay: dict[Category, float]
    bonus_category: Category


SPECIES_TRAITS: dict[Species, SpeciesTrait] = {
    Species.FINIK: SpeciesTrait({Category.WATER: 1.5}, bonus_category=Category.WATER),
    Species.CACTUS: SpeciesTrait(
        {Category.FOOD: 0.5, Category.WATER: 0.7}, bonus_category=Category.FOOD
    ),
    Species.SPARK: SpeciesTrait({Category.PLAY: 1.5}, bonus_category=Category.PLAY),
}

# Опыт. Стадии открываются по порогам; названия совпадают с growthStages клиента.
XP_PER_CARE = 2
XP_CARE_TRAIT_BONUS = 1
XP_GOOD_DAY = 5  # все потребности выше 50 на конец дня
XP_WEEK_NO_OVERRUN = 10
XP_PER_SAVED_COIN = 1
XP_OVERRUN_PENALTY = 5

STAGE_THRESHOLDS: tuple[int, ...] = (0, 100, 200, 300, 400)
STAGE_NAMES: tuple[str, ...] = ("Семечко", "Росток", "Кустик", "Молодое дерево", "Дерево")

DEFAULT_GOAL_TITLE = "Солнечное окно и большой горшок"
DEFAULT_GOAL_TARGET = 150


def stage_for_xp(xp: int) -> int:
    stage = 0
    for index, threshold in enumerate(STAGE_THRESHOLDS):
        if xp >= threshold:
            stage = index
    return stage


def mood_for_needs(values: list[int]) -> Mood:
    """В макете улыбка при среднем уровне потребностей выше 55."""
    average = sum(values) / len(values) if values else 0
    if average > 75:
        return Mood.HAPPY
    if average > 55:
        return Mood.OKAY
    if average > 35:
        return Mood.BORED
    return Mood.SAD


def decay_for(species: Species, category: Category) -> int:
    base = DAILY_DECAY[category]
    factor = SPECIES_TRAITS[species].decay.get(category, 1.0)
    return round(base * factor)
