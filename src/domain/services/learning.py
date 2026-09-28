"""Повторение финансовых навыков с проверкой ответа на сервере."""

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

TOPIC_TITLES = {
    "lesson_discount": "Скидка",
    "lesson_need_want": "Нужды и желания",
    "lesson_budget": "Бюджет",
    "lesson_saving": "Накопления",
    "lesson_compare": "Сравнение цен",
    "lesson_earn": "Доход и расходы",
    "lesson_debt": "Цена долга",
}


@dataclass(frozen=True, slots=True)
class ReviewQuestion:
    topic: str
    title: str
    question: str
    options: tuple[str, str, str]
    right_index: int
    explanation: str


def next_due(streak: int, today: date, *, missed: bool = False) -> date:
    days = 1 if missed else min(2 ** min(streak, 3), 7)
    return today + timedelta(days=days)


def review_question(topic: str, player_id: str, today: date) -> ReviewQuestion:
    """Числа и порядок ответов меняются по дням, проверка остаётся на сервере."""
    base = _base_question(topic, player_id, today)
    seed = int(hashlib.sha256(f"options:{topic}:{player_id}:{today}".encode()).hexdigest()[:8], 16)
    offset = seed % len(base.options)
    options = base.options[offset:] + base.options[:offset]
    return ReviewQuestion(
        base.topic, base.title, base.question, options,
        (base.right_index - offset) % len(options), base.explanation,
    )


def _base_question(topic: str, player_id: str, today: date) -> ReviewQuestion:
    seed = int(hashlib.sha256(f"{topic}:{player_id}:{today}".encode()).hexdigest()[:8], 16)
    variant = seed % 3
    title = TOPIC_TITLES[topic]
    if topic == "lesson_discount":
        old = 10 + variant * 5
        saving = old // 5
        right = old - saving
        return ReviewQuestion(
            topic, title,
            f"Вещь стоила {old} монет. Скидка равна {saving} монетам. Сколько заплатишь?",
            (f"{right}", f"{old}", f"{saving}"), 0,
            f"{old} - {saving} = {right}. Скидку вычитают из старой цены.",
        )
    if topic == "lesson_need_want":
        wants = ("наклейку", "мяч", "ленточку")
        return ReviewQuestion(
            topic, title,
            f"Питомцу нужна вода, а в лавке есть {wants[variant]}. Что купить сначала?",
            ("Воду", wants[variant].capitalize(), "Обе вещи сразу"), 0,
            "Вода закрывает нужду питомца. Желание можно исполнить позже.",
        )
    if topic == "lesson_budget":
        income = 16 + variant * 4
        food, water = 6, 4
        right = income - food - water
        return ReviewQuestion(
            topic, title,
            f"Есть {income} монет. На еду уйдёт {food}, на воду {water}. Сколько останется?",
            (f"{right}", f"{income - food}", f"{income + water}"), 0,
            f"{income} - {food} - {water} = {right}. Сначала учти обе нужды.",
        )
    if topic == "lesson_saving":
        target = 20 + variant * 5
        saved = 6 + variant
        right = target - saved
        return ReviewQuestion(
            topic, title,
            f"Мечта стоит {target} монет, в копилке {saved}. Сколько осталось накопить?",
            (f"{right}", f"{target}", f"{target + saved}"), 0,
            f"{target} - {saved} = {right}. Уже накопленное вычитают из цены мечты.",
        )
    if topic == "lesson_compare":
        small_price = 6 + variant * 3
        large_price = 8 + variant * 4
        return ReviewQuestion(
            topic, title,
            f"3 семечка стоят {small_price}, 5 семечек стоят {large_price}. Где одно дешевле?",
            ("Набор из пяти", "Набор из трёх", "Цена одинаковая"), 0,
            f"{small_price} / 3 = {small_price // 3}, "
            f"а {large_price} / 5 = {large_price / 5:g}. Сравни цену одной штуки.",
        )
    if topic == "lesson_earn":
        income = 12 + variant * 4
        costs = 3 + variant
        right = income - costs
        return ReviewQuestion(
            topic, title,
            f"За помощь дали {income} монет, материалы стоили {costs}. Сколько заработано?",
            (f"{right}", f"{income}", f"{costs}"), 0,
            f"{income} - {costs} = {right}. Заработок считают после расходов.",
        )
    if topic == "lesson_debt":
        borrowed = 8 + variant * 2
        extra = 2 + variant
        repayment = borrowed + extra
        return ReviewQuestion(
            topic, title,
            f"Взял {borrowed} монет, вернуть нужно {repayment}. Сколько стоит такой долг?",
            (f"{extra}", f"{borrowed}", f"{repayment}"), 0,
            f"{repayment} - {borrowed} = {extra}. Это переплата за долг.",
        )
    raise ValueError("Неизвестная тема повторения")
