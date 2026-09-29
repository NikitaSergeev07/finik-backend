"""Голоса питомцев и заготовленные фразы для работы без модели."""

import hashlib
from collections.abc import Sequence

from domain import rules
from domain.entities import Goal, LogEntry, Pet, Week
from domain.enums import ActionKind, Category, Mood, Species

CATEGORY_RU: dict[Category, str] = {
    Category.FOOD: "еда",
    Category.WATER: "вода",
    Category.PLAY: "игры",
    Category.SAVE: "копилка",
}

MOOD_RU: dict[Mood, str] = {
    Mood.HAPPY: "рад",
    Mood.OKAY: "в порядке",
    Mood.BORED: "скучает",
    Mood.SAD: "грустит",
}

SPECIES_RU: dict[Species, dict[str, str]] = {
    Species.OWL: {
        "title": "сова",
        "trait": "любит заботу и учится планировать",
        "style": "спокойная, любопытная и дружелюбная",
    },
    Species.FINIK: {
        "title": "лиса",
        "trait": "пьёт много воды",
        "style": "хитрая и наблюдательная; любит находить умный путь к мечте",
    },
    Species.CACTUS: {
        "title": "хомяк",
        "trait": "бережливый, редко просит еду",
        "style": "запасливый и добрый; радуется монетам в копилке",
    },
    Species.SPARK: {
        "title": "кот",
        "trait": "скучает быстрее и любит игры",
        "style": "игривый и любопытный; иногда мурлычет, но помнит план",
    },
}

REDIRECT = "Давай лучше про монеты и копилку. Что отложишь сегодня, а что подождёт?"
CHAT_TIRED = "Я уже наболтался за сегодня. Завтра снова поговорим - и про мечту тоже."

VOICE_OPENING: dict[Species, str] = {
    Species.OWL: "Угу, я прикинула: ",
    Species.FINIK: "Лисья хитрость подсказывает мне: ",
    Species.CACTUS: "Мои хомячьи запасы говорят: ",
    Species.SPARK: "Мур, я прикинул: ",
}


def pick(items: Sequence[str], seed: str) -> str:
    """Стабильный выбор фразы: один и тот же день даёт одну и ту же реплику."""
    digest = hashlib.sha256(seed.encode()).digest()
    return items[int.from_bytes(digest[:4], "big") % len(items)]


def lowest_need(pet: Pet) -> Category:
    needs = [(cat, pet.needs[cat]) for cat in Category if cat.is_need]
    return min(needs, key=lambda pair: pair[1])[0]


def remark_fallback(pet: Pet, week: Week, goal: Goal | None = None) -> str:
    seed = f"{pet.id}:{week.number}:{week.day}:{pet.mood}:{lowest_need(pet)}"
    low = CATEGORY_RU[lowest_need(pet)]
    save_left = week.entry(Category.SAVE).left
    name = pet.name
    if pet.mood is Mood.HAPPY:
        return VOICE_OPENING[pet.species] + pick(
            (
                f"{name} доволен: воды и еды хватает. Можно ещё {save_left} в копилку на мечту.",
                f"{name}: мне хорошо. Если останутся монеты - спрячем в мечту, не в игрушки.",
            ),
            seed,
        )
    if pet.mood is Mood.OKAY:
        return VOICE_OPENING[pet.species] + pick(
            (
                f"{name} в порядке. Глянь статью «{low}»: там запас тоньше остальных.",
                f"{name}: день {week.day} из 7. Я держусь, но «{low}» скоро попросит монет.",
            ),
            seed,
        )
    if pet.mood is Mood.BORED:
        return VOICE_OPENING[pet.species] + pick(
            (
                f"{name} скучает. Проверь, в какой статье остались монеты - особенно «{low}».",
                f"{name} скучает. Если в плане ещё есть монеты на «{low}» - самое время.",
            ),
            seed,
        )
    saved = f", в мечте уже {goal.saved}" if goal else ""
    return VOICE_OPENING[pet.species] + pick(
        (
            f"{name} грустит: «{low}» на нуле. Сначала уход, копилка подождёт{saved}.",
            f"{name} плохо без «{low}». Давай сначала план, потом покупки.",
        ),
        seed,
    )


def week_summary_fallback(week: Week, goal: Goal) -> str:
    spent_needs = sum(week.entry(cat).spent for cat in Category if cat.is_need)
    saved = week.entry(Category.SAVE).spent
    if week.overrun:
        return (
            f"Неделя {week.number}: план {week.income}, на уход ушло {spent_needs}, "
            f"в мечту {saved}. Был перерасход {week.overrun} - копилка стала тоньше, "
            f"но мечта «{goal.title}» всё ещё с нами."
        )
    if saved * 5 >= week.income:
        return (
            f"Неделя {week.number} вышла ровной: уход {spent_needs}, в мечту {saved} "
            f"из {week.income}. Так «{goal.title}» становится ближе."
        )
    return (
        f"Неделя {week.number}: потратили {spent_needs}, отложили {saved}. "
        f"В следующий раз можно чуть больше спрятать в копилку - мечта не убежит."
    )


def diary_fallback(pet: Pet, day: int, entries: list[LogEntry]) -> str:
    if not entries:
        return (
            f"День {day}. {VOICE_OPENING[pet.species]}сегодня мы отдыхали. "
            "Завтра проверим план и добавим монету к мечте."
        )
    bits: list[str] = []
    if any(e.kind is ActionKind.CARE for e in entries):
        bits.append("ты за мной ухаживал")
    if any(e.kind is ActionKind.PURCHASE for e in entries):
        bits.append("мы заглянули в лавку")
    if any(e.kind is ActionKind.DEPOSIT for e in entries):
        bits.append("в мечту упали монеты")
    if any(e.kind is ActionKind.OVERRUN for e in entries):
        bits.append("пришлось взять из копилки")
    if any(e.kind is ActionKind.EVENT_CHOICE for e in entries):
        bits.append("случилась история")
    body = ", ".join(bits) if bits else "день прошёл тихо"
    return f"День {day}. {pet.name} пишет: {VOICE_OPENING[pet.species]}{body}. Я это запомню."


def dream_steps(goal: Goal, weekly_save: int) -> tuple[int, int, list[tuple[str, int]]]:
    """Счёт без модели: сколько копить и какими шагами. ИИ пишет только совет."""
    remain = max(0, goal.target - goal.saved)
    weekly = max(1, weekly_save)
    weeks_left = 0 if remain == 0 else (remain + weekly - 1) // weekly
    if remain == 0:
        return remain, weekly, [("Мечта собрана - можно выбирать покупку", 0)]
    first = min(weekly, remain)
    steps = [("На этой неделе отложи в копилку", first)]
    rest = remain - first
    if rest:
        more = max(weeks_left - 1, 1)
        steps.append((f"Повтори ещё {more} нед.", rest))
    steps.append(("Когда копилка дотянет - купи мечту", 0))
    return remain, weekly, steps


def dream_speedup(play_planned: int, remain: int, weekly_save: int) -> tuple[int, int, int]:
    """Если урезать игры на DREAM_SPEEDUP_CUT и добавить в копилку - на сколько недель раньше."""
    cut = min(rules.DREAM_SPEEDUP_CUT, max(0, play_planned))
    weekly = max(1, weekly_save)
    if remain <= 0 or cut <= 0:
        return 0, weekly, 0
    weeks_now = (remain + weekly - 1) // weekly
    faster = weekly + cut
    weeks_new = (remain + faster - 1) // faster
    return cut, faster, max(0, weeks_now - weeks_new)


def dream_advice_fallback(
    goal: Goal,
    weekly_save: int,
    weeks_left: int,
    *,
    cut: int = 0,
    weeks_saved: int = 0,
) -> str:
    if goal.saved >= goal.target:
        return f"«{goal.title}» уже в кармане. Можно радоваться и не тратить копилку впустую."
    text = (
        f"До «{goal.title}» осталось {goal.target - goal.saved} монет. "
        f"По {max(1, weekly_save)} в неделю - это примерно {weeks_left} нед. "
        "Главное не забирать из копилки на игрушки."
    )
    if weeks_saved:
        return (
            f"{text} Если урезать игры на {cut} и добавить в копилку - "
            f"на {weeks_saved} нед. раньше."
        )
    if cut:
        return f"{text} Если урезать игры на {cut} и добавить в копилку, шаги станут крупнее."
    return text


_ORIGIN: dict[Species, tuple[str, str, str]] = {
    Species.OWL: (
        "{name} — маленькая сова, которая нашла копилку у своего гнезда.",
        "Она мечтает об уютном доме, любит играть и учится беречь монеты.",
        "Вместе с тобой {name} сначала планирует заботу, потом копилку и развлечения.",
    ),
    Species.FINIK: (
        "{name} - молодая лиса. Она нашла пустую шкатулку "
        "и решила наполнить её монетами для мечты.",
        "Лиса любит воду после прогулок и замечает, какая покупка может подождать.",
        "Теперь {name} учится хитрому плану: сначала нужное, "
        "потом копилка, а развлечения - на остаток.",
    ),
    Species.CACTUS: (
        "{name} - хомяк, который нашёл красивую пустую коробочку и назвал её копилкой.",
        "Он бережёт запасы и радуется каждой монете для мечты.",
        "Если монет не хватает, {name} ждёт неделю, а не забирает из копилки.",
    ),
    Species.SPARK: (
        "{name} - кот, который увидел блестящую монету и придумал большую мечту.",
        "Играть он готов весь день, но все монеты на забавы тратить скучно: мечта не приблизится.",
        "Теперь {name} мурлычет над планом и оставляет часть монет в копилке каждую неделю.",
    ),
}


def origin_fallback(species: Species, name: str) -> str:
    """Три коротких абзаца истории. Без модели - тот же тон, что у живого ответа."""
    parts = _ORIGIN[species]
    return "\n\n".join(part.format(name=name) for part in parts)
