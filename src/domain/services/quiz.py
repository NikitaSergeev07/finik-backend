"""Вопросы по ценам лавки. Правильный ответ считает сервер, не модель."""

import hashlib
from dataclasses import dataclass

from domain.entities import ShopItem
from domain.services.persona import pick


@dataclass(frozen=True, slots=True)
class PriceQuestion:
    index: int
    question: str
    options: list[str]
    right_index: int
    explanation: str


def build_questions(items: list[ShopItem], kind: str, seed: str) -> list[PriceQuestion]:
    """1–3 вопроса из текущих цен. kind: quiz | riddle - только формулировка."""
    priced = sorted((i for i in items if i.cost > 0), key=lambda i: i.slug)
    if len(priced) < 2:
        return []
    riddle = kind == "riddle"
    builders = (_q_discount, _q_how_many, _q_sum)
    out: list[PriceQuestion] = []
    for builder in builders:
        built = builder(priced, riddle, f"{seed}:{len(out)}")
        if built is None:
            continue
        question, options, right, explanation = built
        out.append(PriceQuestion(len(out), question, options, right, explanation))
        if len(out) == 3:
            break
    return out


def _q_discount(
    items: list[ShopItem], riddle: bool, seed: str
) -> tuple[str, list[str], int, str] | None:
    sale = [i for i in items if i.old_cost and i.old_cost > i.cost]
    if not sale:
        return None
    item = pick(sale, seed)
    assert item.old_cost is not None
    diff = item.old_cost - item.cost
    if riddle:
        question = (
            f"Я стоил {item.old_cost} монет, а теперь стою {item.cost}. "
            "Сколько монет ты сохранишь для мечты?"
        )
        options, right = _three(diff, seed, suffix="")
        explain = f"{item.old_cost} - {item.cost} = {diff}. Столько монет остаётся у тебя."
    else:
        pct = item.sale_percent
        question = (
            f"Товар «{item.name}»: старая цена {item.old_cost}, новая {item.cost}. "
            "Примерно сколько это скидка в процентах?"
        )
        options, right = _three(pct, seed, suffix="%")
        explain = f"{item.name}: {item.old_cost} - {item.cost} = {diff}, это примерно {pct}%."
    return question, options, right, explain


def _q_how_many(
    items: list[ShopItem], riddle: bool, seed: str
) -> tuple[str, list[str], int, str] | None:
    pairs = [
        (cheap, expensive)
        for cheap in items
        for expensive in items
        if cheap.slug != expensive.slug and expensive.cost >= cheap.cost * 2
    ]
    if not pairs:
        return None
    cheap, expensive = _choose(pairs, seed)
    n = expensive.cost // cheap.cost
    question = (
        f"Сколько «{cheap.name}» спрячется в цене «{expensive.name}»?"
        if riddle
        else (
            f"«{expensive.name}» стоит {expensive.cost}, «{cheap.name}» - {cheap.cost}. "
            f"Сколько дешёвых вещей выйдет на одну дорогую?"
        )
    )
    options, right = _three(n, seed, suffix=" шт.")
    leftover = expensive.cost % cheap.cost
    explain = f"{expensive.cost} ÷ {cheap.cost} = {n}, остаток {leftover} не считаем."
    return question, options, right, explain


def _q_sum(
    items: list[ShopItem], riddle: bool, seed: str
) -> tuple[str, list[str], int, str] | None:
    pairs = [(a, b) for index, a in enumerate(items) for b in items[index + 1 :]]
    if not pairs:
        return None
    a, b = _choose(pairs, seed)
    total = a.cost + b.cost
    question = (
        f"Две покупки: {a.name} и {b.name}. Сколько монет на обе?"
        if riddle
        else f"{a.name} ({a.cost}) плюс {b.name} ({b.cost}). Сколько вместе?"
    )
    options, right = _three(total, seed, suffix=" монет")
    explain = f"{a.cost} + {b.cost} = {total}."
    return question, options, right, explain


def _three(right: int, seed: str, *, suffix: str) -> tuple[list[str], int]:
    distractors = [max(0, right - 2), right + 2, right * 2 if right else 3, max(1, right // 2)]
    wrongs: list[int] = []
    for value in distractors:
        if value != right and value not in wrongs:
            wrongs.append(value)
        if len(wrongs) == 2:
            break
    while len(wrongs) < 2:
        candidate = (wrongs[-1] + 3) if wrongs else right + 3
        if candidate != right and candidate not in wrongs:
            wrongs.append(candidate)
    values = [right, *wrongs]
    shift = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(values)
    ordered = values[shift:] + values[:shift]
    options = [f"{n}{suffix}" for n in ordered]
    return options, ordered.index(right)


def _choose[T](items: list[T], seed: str) -> T:
    index = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(items)
    return items[index]
