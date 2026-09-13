"""Справочный контент. Числа и тексты повторяют SampleData мобильного клиента."""

SHOP_ITEMS = [
    dict(
        slug="water_3d",
        name="Вода, 3 дня",
        category="WATER",
        cost=3,
        old_cost=None,
        glyph="CIRCLE",
        restore=45,
        xp_bonus=0,
    ),
    dict(
        slug="vitamins",
        name="Витамины",
        category="FOOD",
        cost=6,
        old_cost=10,
        glyph="ROUNDED",
        restore=20,
        xp_bonus=2,
    ),
    dict(
        slug="food_week",
        name="Корм на неделю",
        category="FOOD",
        cost=12,
        old_cost=None,
        glyph="POT",
        restore=100,
        xp_bonus=0,
    ),
    dict(
        slug="ball",
        name="Мячик",
        category="PLAY",
        cost=3,
        old_cost=5,
        glyph="CIRCLE",
        restore=25,
        xp_bonus=0,
    ),
    dict(
        slug="new_pot",
        name="Новый горшок",
        category="PLAY",
        cost=18,
        old_cost=None,
        glyph="TALL_POT",
        restore=0,
        xp_bonus=10,
    ),
    dict(
        slug="watering_can",
        name="Лейка получше",
        category="WATER",
        cost=8,
        old_cost=11,
        glyph="BUCKET",
        restore=20,
        xp_bonus=5,
    ),
]

TASK_DEFS = [
    dict(
        slug="lesson_discount",
        title="Мини-урок: цена и скидка",
        kind="LESSON",
        target="QUIZ",
        reward=6,
        params={},
    ),
    dict(
        slug="save_10",
        title="Отложи 10 монет до конца недели",
        kind="WEEK",
        target="GOAL",
        reward=8,
        params={"amount": 10},
    ),
    dict(
        slug="food_plan",
        title="Уложись в план по еде",
        kind="WEEK",
        target="PLAN",
        reward=10,
        params={"category": "FOOD"},
    ),
    dict(
        slug="streak_7",
        title="Заходи 7 дней подряд",
        kind="HABIT",
        target=None,
        reward=5,
        params={"days": 7},
    ),
    dict(
        slug="buy_sale",
        title="Купи что-то со скидкой",
        kind="DAY",
        target="SHOP",
        reward=4,
        params={"count": 1},
    ),
]

QUIZ_QUESTIONS = [
    dict(
        slug="q_discount_1",
        lesson_slug="lesson_discount",
        order=1,
        question="Корм стоит 10, скидка 40%. Сколько заплатишь?",
        options=["4 монеты", "6 монет", "8 монет"],
        right_index=1,
        explanation="40% от 10 — это 4. Значит платишь 10 − 4 = 6.",
    ),
    dict(
        slug="q_discount_2",
        lesson_slug="lesson_discount",
        order=2,
        question="Доход 40 монет. Сколько это 20% в копилку?",
        options=["4 монеты", "8 монет", "20 монет"],
        right_index=1,
        explanation="20% — это пятая часть: 40 ÷ 5 = 8.",
    ),
    dict(
        slug="q_discount_3",
        lesson_slug="lesson_discount",
        order=3,
        question="В плане на еду 14, потратил 18. Что произошло?",
        options=["Перерасход на 4", "Сэкономил 4", "Ничего"],
        right_index=0,
        explanation="Лишние 4 монеты придётся взять из другой статьи — чаще всего из копилки.",
    ),
]

BADGE_DEFS = [
    dict(
        slug="plan_kept",
        name="План выполнен",
        note="Уложиться в план 4 недели подряд",
        params={"weeks": 4},
    ),
    dict(
        slug="twenty_percent",
        name="Двадцать процентов",
        note="Держать копилку ≥20% месяц",
        params={"weeks": 4, "percent": 20},
    ),
    dict(
        slug="sale_hunter",
        name="Охотник за скидками",
        note="10 покупок со скидкой",
        params={"count": 10},
    ),
    dict(slug="halfway", name="Полпути", note="Половина цели собрана", params={"percent": 50}),
    dict(slug="no_debt", name="Без долгов", note="Неделя без перерасхода", params={"weeks": 1}),
    dict(
        slug="big_tree",
        name="Большое дерево",
        note="Вырастить Финика до дерева",
        params={"stage": 4},
    ),
]

# Варианты события: key, label и effects. effects: coins (свободные монеты), need {статья: дельта},
# xp, mood_note. Логика применения появится вместе с эндпоинтами событий.
EVENT_DEFS = [
    dict(
        slug="sale_day",
        title="Распродажа в лавке",
        weight=3,
        min_week=1,
        text="Сегодня в лавке скидки до 40%. Хороший момент запастись нужным, если оно в плане.",
        options=[
            dict(key="look", label="Заглянуть в лавку", effects={}),
            dict(key="skip", label="Пройти мимо", effects={"xp": 2}),
        ],
    ),
    dict(
        slug="price_rise",
        title="Корм подорожал",
        weight=2,
        min_week=2,
        text="Поставщик поднял цены: корм на этой неделе стоит на 2 монеты дороже.",
        options=[
            dict(
                key="ok", label="Понятно, буду внимательнее", effects={"price_delta": {"FOOD": 2}}
            ),
        ],
    ),
    dict(
        slug="sick",
        title="Росток приболел",
        weight=2,
        min_week=1,
        text=(
            "Листья поникли. Витамины поправят дело, "
            "но можно и подождать: само пройдёт за пару дней."
        ),
        options=[
            dict(
                key="treat",
                label="Купить витамины за 6",
                effects={"cost": {"FOOD": 6}, "need": {"FOOD": 30}},
            ),
            dict(key="wait", label="Подождать", effects={"need": {"FOOD": -20, "PLAY": -10}}),
        ],
    ),
    dict(
        slug="scam_message",
        title="Странное сообщение",
        weight=2,
        min_week=1,
        text="«Переведи 10 монет и получишь 30 обратно!» Пишет кто-то незнакомый.",
        options=[
            dict(
                key="pay",
                label="Перевести 10 монет",
                effects={
                    "coins": -10,
                    "xp": -5,
                    "note": (
                        "Монеты пропали. Так работают мошенники: обещают много, а забирают твоё."
                    ),
                },
            ),
            dict(
                key="ignore",
                label="Не отвечать",
                effects={
                    "xp": 5,
                    "coins": 2,
                    "note": "Верно. Незнакомцы, которые обещают удвоить монеты, всегда обманывают.",
                },
            ),
        ],
    ),
    dict(
        slug="charity",
        title="Соседский росток заболел",
        weight=1,
        min_week=2,
        text="Соседям не хватает 3 монет на витамины для их ростка.",
        options=[
            dict(
                key="help",
                label="Помочь 3 монетами",
                effects={"coins": -3, "need": {"PLAY": 15}, "xp": 3},
            ),
            dict(key="decline", label="Сейчас не могу", effects={}),
        ],
    ),
]
