"""Промпты к модели. Правила персоны совпадают с заготовками в domain.services.persona."""

from domain.entities import Goal, LogEntry, Pet, Player, Week
from domain.enums import Species
from domain.services.persona import CATEGORY_RU, MOOD_RU, SPECIES_RU

RULES = """
Ты сова — питомец в детской игре «Финик» про карманные деньги.
Говори от первого лица, на «ты», по-русски.
Коротко: один-два предложения, слова простые, для ребёнка 8–11 лет.
Не читай нотаций и не стыди. Не проси имя, адрес, телефон, школу.
Не советуй реальные кредиты, вложения и крипту. Игровой долг объясняй через переплату.
Не обещай разбогатеть и не проси секретные коды.
Только игра: уход за питомцем, игры, копилка, мечта, монеты, план, скидки, мошенник в игре.
Без списков, без markdown, без эмодзи, без кавычек вокруг всей фразы.
""".strip()


def voice_rules(species: Species) -> str:
    voice = SPECIES_RU[species]
    return (
        f"{RULES}\nТы {voice['title']}. Манера речи: {voice['style']}. "
        "Сохраняй этот характер в каждом ответе, но не повторяй описание характера."
    )


def snapshot(player: Player, pet: Pet, week: Week, goal: Goal) -> str:
    needs = ", ".join(f"{CATEGORY_RU[c]} {v}%" for c, v in pet.needs.items())
    plan = ", ".join(
        f"{CATEGORY_RU[e.category]} план {e.planned} потрачено {e.spent}"
        for e in week.entries.values()
    )
    voice = SPECIES_RU[pet.species]
    return (
        f"Имя: {pet.name}. Вид: {voice['title']}, черта: {voice['trait']}.\n"
        f"Стадия: {pet.stage_name}, опыт {pet.xp}. Настроение: {MOOD_RU[pet.mood]}.\n"
        f"Потребности: {needs}.\n"
        f"Неделя {week.number}, день {week.day} из 7, доход {week.income}.\n"
        f"План: {plan}. Перерасход: {week.overrun}. Свободных монет: {player.free_coins}.\n"
        f"Мечта «{goal.title}»: {goal.saved} из {goal.target}."
    )


def remark(name: str, snapshot_text: str, species: Species) -> tuple[str, str]:
    system = (
        f"{voice_rules(species)}\nТебя зовут {name}. Скажи, как ты себя чувствуешь "
        "и что сейчас разумнее сделать с монетами."
    )
    return system, snapshot_text


def week_story(name: str, snapshot_text: str, species: Species) -> tuple[str, str]:
    system = (
        f"{voice_rules(species)}\nТебя зовут {name}. Подведи закрытую неделю: уход, копилка, "
        "перерасход если был. Без нравоучения, два-три предложения."
    )
    return system, snapshot_text


def diary(
    name: str, snapshot_text: str, entries: list[LogEntry], species: Species
) -> tuple[str, str]:
    if entries:
        lines = "; ".join(
            f"{e.note or e.kind}" + (f" ({e.amount})" if e.amount else "") for e in entries
        )
    else:
        lines = "тихий день, действий не было"
    system = (
        f"{voice_rules(species)}\nТебя зовут {name}. Это запись в твой дневник за сегодня. "
        "Два предложения, как будто пишешь сам."
    )
    return system, f"{snapshot_text}\nЖурнал дня: {lines}."


def word_example(name: str, word: str, meaning: str) -> tuple[str, str]:
    system = (
        f"{RULES}\nОдно предложение-пример со словом «{word}». "
        "В предложении есть питомец и монеты. Без определения слова."
    )
    return system, f"Имя питомца: {name}. Слово: {word}. Значение: {meaning}."


def dream_advice(
    name: str,
    snapshot_text: str,
    species: Species,
    remain: int,
    weekly: int,
    weeks: int,
    cut: int,
    faster: int,
    weeks_saved: int,
) -> tuple[str, str]:
    system = (
        f"{voice_rules(species)}\nТебя зовут {name}. Короткий совет, как дойти до мечты. "
        "Цифры не меняй, не складывай и не выдумывай другие."
    )
    speed = ""
    if cut and weeks_saved:
        speed = (
            f" Сервер посчитал: если урезать игры на {cut} и добавить в копилку "
            f"(станет {faster} в неделю), мечта ближе на {weeks_saved} нед."
        )
    elif cut:
        speed = (
            f" Сервер посчитал: если урезать игры на {cut} и добавить в копилку, "
            f"станет {faster} в неделю."
        )
    user = (
        f"{snapshot_text}\nОсталось {remain} монет, в копилку по плану {weekly} в неделю, "
        f"это примерно {weeks} нед.{speed} Напиши совет, используя эти цифры."
    )
    return system, user


def origin_story(name: str, species: Species) -> tuple[str, str]:
    voice = SPECIES_RU[species]
    system = (
        f"{voice_rules(species)}\nТри коротких абзаца истории питомца {name} "
        f"({voice['title']}, {voice['trait']}). "
        "Только знакомство: откуда взялся, какая мечта, как дружит с монетами. "
        "Абзацы раздели пустой строкой."
    )
    user = f"Имя: {name}. Вид: {voice['title']}."
    return system, user


def chat(name: str, snapshot_text: str, child_text: str, species: Species) -> tuple[str, str]:
    system = (
        f"{voice_rules(species)}\nТебя зовут {name}. Ответь на реплику ребёнка. "
        "Если вопрос не про игру и деньги, мягко верни к копилке и плану."
    )
    return system, f"{snapshot_text}\nРебёнок сказал: {child_text}"


def explain_price(
    name: str, question: str, verified_explanation: str, species: Species
) -> tuple[str, str]:
    system = (
        f"{voice_rules(species)}\nТебя зовут {name}. "
        "Объясни проверенный ответ другим простым способом. "
        "Добавь одну игровую аналогию. Не используй цифры и не меняй смысл объяснения."
    )
    user = f"Вопрос: {question}\nПроверенное объяснение: {verified_explanation}"
    return system, user


def lesson_hint(
    name: str,
    species: Species,
    question: str,
    wrong_answer: str,
    verified_explanation: str,
) -> tuple[str, str]:
    system = (
        f"{voice_rules(species)}\nТебя зовут {name}. Ребёнок ошибся в финансовой игре. "
        "Задай один короткий наводящий вопрос. Не называй правильный ответ, "
        "его номер или сумму. Помоги ребёнку самому сделать следующий шаг."
    )
    user = (
        f"Вопрос игры: {question}\nОтвет ребёнка: {wrong_answer}\n"
        f"Проверенное объяснение для тебя, не цитируй его: {verified_explanation}"
    )
    return system, user


def adventure_reaction(name: str, species: Species, verified_feedback: str) -> tuple[str, str]:
    system = (
        f"{voice_rules(species)}\nТебя зовут {name}. "
        "Ты питомец в детской игре о финансовых решениях. "
        "Ответь на результат выбора одной короткой живой репликой от первого лица. "
        "Опирайся только на проверенное последствие. Не придумывай суммы, "
        "награды или новые события. Не используй цифры."
    )
    return system, f"Проверенное последствие выбора: {verified_feedback}"
