"""Числа и правила игры в одном месте. Менять баланс — здесь, а не по коду."""

from dataclasses import dataclass

from core.errors import RuleViolation
from domain.enums import Category, Mood, Species

DAYS_IN_WEEK = 7
STREAK_LABELS: tuple[str, ...] = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
STREAK_BONUS = 5  # монеты за семь дней подряд, когда неделя закрывается
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
    Category.WATER: CareAction(Category.WATER, "Напоить", cost=2, restore=22),
    Category.FOOD: CareAction(Category.FOOD, "Покормить", cost=3, restore=22),
    Category.PLAY: CareAction(Category.PLAY, "Поиграть", cost=2, restore=22),
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
    rare: bool = False


SPECIES_TRAITS: dict[Species, SpeciesTrait] = {
    Species.OWL: SpeciesTrait({}, bonus_category=Category.SAVE),
    Species.FINIK: SpeciesTrait({Category.WATER: 1.5}, bonus_category=Category.WATER),
    Species.CACTUS: SpeciesTrait(
        {Category.FOOD: 0.5, Category.WATER: 0.7}, bonus_category=Category.FOOD
    ),
    # Редкий огонёк: на закрытии недели чуть возвращает монеты с остатка игр.
    Species.SPARK: SpeciesTrait({Category.PLAY: 1.5}, bonus_category=Category.PLAY, rare=True),
}

# Опыт. Стадии открываются по порогам; названия совпадают с growthStages клиента.
XP_PER_CARE = 1
XP_CARE_TRAIT_BONUS = 1
XP_GOOD_DAY = 5  # все потребности выше 50 на конец дня
XP_WEEK_NO_OVERRUN = 10
XP_PER_SAVED_COIN = 1
XP_OVERRUN_PENALTY = 5
# Увядание: потребность на нуле в конце дня. Мягко для 8–11: −20 опыта,
# и если росток уже не семечко — откат ровно на одну стадию (под порог текущей).
WILT_XP_LOSS = 20

STAGE_THRESHOLDS: tuple[int, ...] = (0, 100, 200, 300, 400)
STAGE_NAMES: tuple[str, ...] = ("Малыш", "Непоседа", "Подросток", "Взрослый друг", "Мудрый друг")

LOOK_VARIANTS = 6  # BLUE, DESERT_SAND, FIERY_RED, FOREST_GREEN, NIGHT_PURPLE, SNOWY_WHITE


@dataclass(frozen=True, slots=True)
class GoalOption:
    slug: str
    title: str
    target: int
    why: str


GOAL_CATALOG: tuple[GoalOption, ...] = (
    GoalOption(
        "sunny_window",
        "Уютное гнездо у окна",
        150,
        "Сове нужен уютный дом и место для отдыха — это большая, но понятная мечта.",
    ),
    GoalOption(
        "watering_kit",
        "Набор для заботы",
        80,
        "Поилка и запас корма. Обязательный уход станет проще.",
    ),
    GoalOption(
        "play_garden",
        "Игровая площадка",
        120,
        "Место для игр. Это желаемое: можно подождать, если копилка тонкая.",
    ),
)

DEFAULT_GOAL_TITLE = GOAL_CATALOG[0].title
DEFAULT_GOAL_TARGET = GOAL_CATALOG[0].target


def goal_by_slug(slug: str | None) -> GoalOption:
    if slug:
        for option in GOAL_CATALOG:
            if option.slug == slug:
                return option
        raise RuleViolation("Такой мечты нет. Выбери одну из трёх.")
    return GOAL_CATALOG[0]


def look_variant_or_raise(value: int) -> int:
    if value not in range(LOOK_VARIANTS):
        raise RuleViolation("Такого цвета нет. Выбери один из шести.")
    return value


# Копилка: на закрытии недели остаток SAVE растёт на 5%, дробь отбрасывается.
SAVINGS_INTEREST_PCT = 5

# Редкий вид (SPARK): 10% остатка бонусной статьи, минимум 1, максимум 2 монеты.
CASHBACK_PERCENT = 10
CASHBACK_MAX = 2

# Множители недели: лавка дорожает, задания чуть жёстче. Дальше таблицы — шаг и потолок.
WEEK_PRICE_MULT: dict[int, float] = {
    1: 1.00,
    2: 1.05,
    3: 1.10,
    4: 1.15,
    5: 1.20,
    6: 1.25,
    7: 1.30,
    8: 1.35,
}
WEEK_PRICE_STEP = 0.05
WEEK_PRICE_MULT_CAP = 1.50

WEEK_TASK_MULT: dict[int, float] = {
    1: 1.00,
    2: 1.10,
    3: 1.20,
    4: 1.30,
    5: 1.40,
    6: 1.50,
    7: 1.60,
    8: 1.70,
}
WEEK_TASK_STEP = 0.10
WEEK_TASK_MULT_CAP = 2.00
WEEK_TASK_STRICT_FROM = 4  # food_plan с 4-й недели ещё и без перерасхода

# План мечты: сервер считает, на сколько недель раньше, если урезать игры.
DREAM_SPEEDUP_CUT = 2

PARENT_BONUS_MIN = 1
PARENT_BONUS_MAX = 20

QUIZ_REWARD = 2  # монеты за первый верный ответ викторины/загадки за игровой день

# ИИ: сколько раз за игровой день можно спросить ростка. Дальше — заготовленная фраза.
AI_CHAT_PER_DAY = 12
AI_REMARK_SENTENCES = 2
AI_REMARK_CHARS = 220
AI_STORY_CHARS = 420
AI_CHAT_CHARS = 280
AI_ORIGIN_CHARS = 720
AI_ORIGIN_SENTENCES = 9


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


def _week_factor(table: dict[int, float], week_number: int, *, cap: float, step: float) -> float:
    n = max(1, week_number)
    if n in table:
        return table[n]
    return min(cap, round(1.0 + (n - 1) * step, 2))


def week_price_factor(week_number: int) -> float:
    """Цены лавки: неделя 1 = 1.0, дальше +5% за неделю, не выше 1.5."""
    return _week_factor(WEEK_PRICE_MULT, week_number, cap=WEEK_PRICE_MULT_CAP, step=WEEK_PRICE_STEP)


def week_task_factor(week_number: int) -> float:
    """Цели заданий: неделя 1 = 1.0, дальше +10% за неделю, не выше 2.0."""
    return _week_factor(WEEK_TASK_MULT, week_number, cap=WEEK_TASK_MULT_CAP, step=WEEK_TASK_STEP)


def scaled_cost(catalog_cost: int, week_number: int, extra: int = 0) -> int:
    """Цена с множителем недели и надбавкой события. Не ниже цены из каталога."""
    raw = round(catalog_cost * week_price_factor(week_number)) + extra
    return max(catalog_cost, raw)


def scaled_task_amount(base: int, week_number: int) -> int:
    return max(base, round(base * week_task_factor(week_number)))


def scaled_task_reward(base: int, week_number: int) -> int:
    """Награда растёт вполовину медленнее цели, чтобы не раздувать доход."""
    factor = week_task_factor(week_number)
    return max(base, round(base * (1 + (factor - 1) * 0.5)))


def savings_interest(leftover: int) -> int:
    """5% от остатка копилки на закрытии недели, дробь отбрасывается."""
    if leftover <= 0:
        return 0
    return leftover * SAVINGS_INTEREST_PCT // 100


def cashback_coins(leftover: int) -> int:
    """Кэшбэк редкого ростка с остатка бонусной статьи. 0, если тратить было нечего."""
    if leftover <= 0:
        return 0
    return min(CASHBACK_MAX, max(1, leftover * CASHBACK_PERCENT // 100))


def wilt_xp(current_xp: int) -> int:
    """Новый опыт после увядания: −WILT_XP_LOSS и откат на стадию, если уже не семечко."""
    xp = max(0, current_xp)
    stage = stage_for_xp(xp)
    dropped = max(0, xp - WILT_XP_LOSS)
    if stage > 0:
        floor = STAGE_THRESHOLDS[stage] - 1
        dropped = min(floor, dropped)
    return dropped
