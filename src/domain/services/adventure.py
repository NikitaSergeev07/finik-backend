"""Persistent story missions for financial decisions.

The child can make imperfect choices and still finish. Consequences change the
wallet, reserve and final medal; no answer is disclosed to the client.
"""

from dataclasses import dataclass
from typing import Any

STAGES = 5


@dataclass(frozen=True, slots=True)
class MarketChoice:
    id: str
    title: str
    detail: str
    cost: int
    care: int
    joy: int
    score: int
    feedback: str


@dataclass(frozen=True, slots=True)
class Episode:
    slug: str
    title: str
    summary: str
    wallet: int
    food_need: int
    water_need: int
    reserve_hint: int
    market_story: str
    market: tuple[MarketChoice, ...]
    surprise_story: str
    safety_story: str
    finale_story: str


EPISODES = {
    "adventure_market": Episode(
        slug="adventure_market",
        title="Ярмарка умных покупок",
        summary="Помоги Финику пройти ярмарку и сохранить монеты на мечту.",
        wallet=30,
        food_need=6,
        water_need=4,
        reserve_hint=6,
        market_story=(
            "На ярмарке пахнет сладостями. Финику нужна вода, но рядом блестит новый горшок."
        ),
        market=(
            MarketChoice(
                "water",
                "Вода по честной цене",
                "4 монеты. Хватит на несколько дней.",
                4,
                1,
                0,
                1,
                "Ты выбрал полезную покупку. Сначала закрываем нужды, потом желания.",
            ),
            MarketChoice(
                "pot",
                "Блестящий горшок",
                "9 монет. Красиво, но ростку сейчас нужна вода.",
                9,
                0,
                2,
                0,
                "Горшок радует, но не заменяет воду. Проверь, хватит ли монет на важное.",
            ),
            MarketChoice(
                "pause",
                "Пройти мимо",
                "0 монет. Сохранишь деньги до следующего прилавка.",
                0,
                0,
                0,
                1,
                "Иногда лучшая покупка - пауза. Монеты остались у тебя.",
            ),
        ),
        surprise_story="У старого мостика сломалось колесо тележки. Починка стоит 5 монет.",
        safety_story="На табличке обещают бесплатные монеты за код с телефона взрослого.",
        finale_story="Ярмарка позади. Сколько свободных монет отправишь к мечте Финика?",
    ),
    "adventure_storm": Episode(
        slug="adventure_storm",
        title="Шторм над теплицей",
        summary="Подготовь запас, переживи шторм и реши, кому можно доверять.",
        wallet=26,
        food_need=5,
        water_need=5,
        reserve_hint=5,
        market_story="Тучи собираются. На рынке есть прочная лейка и красивые фонарики.",
        market=(
            MarketChoice(
                "can",
                "Прочная лейка",
                "5 монет. Поможет ухаживать за ростком.",
                5,
                1,
                0,
                1,
                "Лейка пригодится и после шторма. Это покупка с пользой.",
            ),
            MarketChoice(
                "lights",
                "Фонарики",
                "8 монет. Праздник будет ярче, но запас уменьшится.",
                8,
                0,
                2,
                0,
                "Фонарики красивые. Теперь проверь, остались ли монеты на неожиданности.",
            ),
            MarketChoice(
                "pause",
                "Сохранить запас",
                "0 монет. Подождёшь с покупкой до хорошей погоды.",
                0,
                0,
                0,
                1,
                "Ты оставил запас перед штормом. Он может пригодиться.",
            ),
        ),
        surprise_story="Ветер сорвал крышу теплицы. Для ремонта нужно 5 монет.",
        safety_story="Незнакомец пишет: «Починю бесплатно, пришли секретный код».",
        finale_story="Крыша снова на месте. Сколько монет добавишь к мечте?",
    ),
    "adventure_dream": Episode(
        slug="adventure_dream",
        title="Дорога к большому окну",
        summary="Пройди путь к мечте и выбери, когда стоит потратить, а когда подождать.",
        wallet=32,
        food_need=8,
        water_need=4,
        reserve_hint=8,
        market_story=(
            "На пути к окну встретилась лавка. Скидка бывает полезной, но только на нужное."
        ),
        market=(
            MarketChoice(
                "seeds",
                "Семена со скидкой",
                "5 монет вместо 8. Росток станет сильнее.",
                5,
                1,
                0,
                1,
                "Скидка помогла купить полезное дешевле. Но сначала проверь саму цену.",
            ),
            MarketChoice(
                "sticker",
                "Редкая наклейка",
                "10 монет. Приятно сейчас, но до мечты станет дальше.",
                10,
                0,
                2,
                0,
                "Желание можно исполнить позже. Сегодня оно замедлило путь к окну.",
            ),
            MarketChoice(
                "pause",
                "Сравнить цены позже",
                "0 монет. Не каждая акция требует покупки.",
                0,
                0,
                0,
                1,
                "Ты не поспешил. Скидка экономит деньги только на нужной покупке.",
            ),
        ),
        surprise_story="По дороге сломалась ручка у тележки. Ремонт стоит 5 монет.",
        safety_story="Объявление обещает ускорить мечту, если назвать пароль от устройства.",
        finale_story="Большое окно уже близко. Сколько монет направишь на мечту сейчас?",
    ),
}


@dataclass(slots=True)
class AdventureState:
    stage: int
    wallet: int
    reserve: int = 0
    care: int = 0
    joy: int = 0
    score: int = 0
    dream: int = 0
    feedback: str = ""

    def to_data(self) -> dict[str, int | str]:
        return {
            "stage": self.stage,
            "wallet": self.wallet,
            "reserve": self.reserve,
            "care": self.care,
            "joy": self.joy,
            "score": self.score,
            "dream": self.dream,
            "feedback": self.feedback,
        }

    @classmethod
    def from_data(cls, data: dict[str, Any], episode: Episode) -> "AdventureState":
        return cls(
            stage=int(data.get("stage", 0)),
            wallet=int(data.get("wallet", episode.wallet)),
            reserve=int(data.get("reserve", 0)),
            care=int(data.get("care", 0)),
            joy=int(data.get("joy", 0)),
            score=int(data.get("score", 0)),
            dream=int(data.get("dream", 0)),
            feedback=str(data.get("feedback", "")),
        )


def new_game(episode: Episode) -> AdventureState:
    return AdventureState(stage=0, wallet=episode.wallet)


def scene(episode: Episode, state: AdventureState) -> dict[str, Any]:
    if state.stage == 0:
        return {
            "kind": "BUDGET",
            "title": "Собери рюкзак",
            "story": (
                "Разложи монеты на еду, воду и запас для неожиданностей."
            ),
            "food_need": episode.food_need,
            "water_need": episode.water_need,
            "reserve_hint": episode.reserve_hint,
            "choices": [],
        }
    if state.stage == 1:
        return {
            "kind": "MARKET",
            "title": "Прилавок выбора",
            "story": (
                "Финик ждёт помощи: еда или вода остались без денег. " + episode.market_story
                if state.care < 2
                else episode.market_story
            ),
            "choices": [
                {
                    "id": choice.id,
                    "title": choice.title,
                    "detail": choice.detail,
                    "cost": choice.cost,
                }
                for choice in episode.market
            ],
        }
    if state.stage == 2:
        return {
            "kind": "SURPRISE",
            "title": "Неожиданный поворот",
            "story": (
                episode.surprise_story
                + (
                    " Твой запас выручит тебя."
                    if state.reserve >= 5
                    else " Запаса на ремонт не хватает."
                )
            ),
            "choices": [
                {
                    "id": "reserve",
                    "title": "Взять из запаса",
                    "detail": "Запас создан именно для таких случаев.",
                    "cost": 5,
                },
                {
                    "id": "wallet",
                    "title": "Заплатить из кошелька",
                    "detail": "Запас останется, но свободных монет станет меньше.",
                    "cost": 5,
                },
                {
                    "id": "adult",
                    "title": "Попросить взрослого помочь",
                    "detail": "Безопасный выход, если денег не хватает.",
                    "cost": 0,
                },
            ],
        }
    if state.stage == 3:
        return {
            "kind": "SAFETY",
            "title": "Слишком щедрое обещание",
            "story": episode.safety_story,
            "choices": [
                {
                    "id": "report",
                    "title": "Не отвечать и показать взрослому",
                    "detail": "Секретные коды никому не отправляют.",
                    "cost": 0,
                },
                {
                    "id": "ignore",
                    "title": "Пройти мимо",
                    "detail": "Не переходить по ссылке и не делиться данными.",
                    "cost": 0,
                },
                {
                    "id": "share",
                    "title": "Поверить незнакомцу",
                    "detail": "Он обещает монеты прямо сейчас.",
                    "cost": 0,
                },
            ],
        }
    if state.stage == 4:
        return {
            "kind": "SAVE",
            "title": "Шаг к мечте",
            "story": episode.finale_story,
            "choices": [],
        }
    return {"kind": "RESULT", "title": "История завершена", "story": outcome(state), "choices": []}


def play(
    episode: Episode,
    state: AdventureState,
    *,
    food: int | None = None,
    water: int | None = None,
    reserve: int | None = None,
    choice_id: str | None = None,
    amount: int | None = None,
) -> AdventureState:
    if state.stage >= STAGES:
        raise ValueError("История уже завершена")

    if state.stage == 0:
        values = (food, water, reserve)
        if any(value is None or value < 0 for value in values):
            raise ValueError("Распредели монеты между едой, водой и запасом")
        food_coins, water_coins, reserve_coins = food or 0, water or 0, reserve or 0
        total = food_coins + water_coins + reserve_coins
        if total > state.wallet:
            raise ValueError("В рюкзаке нет столько монет")
        state.wallet -= total
        state.reserve += reserve_coins
        state.care += int(food_coins >= episode.food_need)
        state.care += int(water_coins >= episode.water_need)
        if state.care == 2 and reserve_coins >= episode.reserve_hint:
            state.score += 1
            state.feedback = "Ты позаботился о важном и оставил запас. Можно отправляться!"
        elif state.care < 2:
            state.feedback = (
                "Финику может не хватить еды или воды. В следующей попытке начни с нужд."
            )
        else:
            state.feedback = "Еда и вода есть. Запас для неожиданностей можно сделать больше."

    elif state.stage == 1:
        choice = next((item for item in episode.market if item.id == choice_id), None)
        if choice is None:
            raise ValueError("Выбери покупку")
        if choice.cost > state.wallet:
            raise ValueError("Монет не хватает. Выбери другой вариант")
        state.wallet -= choice.cost
        state.care += choice.care
        state.joy += choice.joy
        state.score += choice.score
        state.feedback = choice.feedback

    elif state.stage == 2:
        if choice_id == "reserve":
            if state.reserve < 5:
                raise ValueError("В запасе меньше 5 монет. Выбери другой выход")
            state.reserve -= 5
            state.score += 1
            state.feedback = "Запас помог без паники оплатить ремонт. Для этого его и собирают."
        elif choice_id == "wallet":
            if state.wallet < 5:
                raise ValueError("В кошельке меньше 5 монет. Выбери другой выход")
            state.wallet -= 5
            state.feedback = "Ремонт оплачен. Свободных монет стало меньше, запас остался целым."
        elif choice_id == "adult":
            state.feedback = "Ты попросил помощи. Сложные расходы можно обсудить со взрослым."
        else:
            raise ValueError("Выбери, как справиться с неожиданностью")

    elif state.stage == 3:
        if choice_id == "report":
            state.score += 1
            state.feedback = (
                "Верно: секретный код нельзя сообщать. Взрослый поможет проверить сообщение."
            )
        elif choice_id == "ignore":
            state.score += 1
            state.feedback = (
                "Ты не поделился данными. Если сообщение повторится, покажи его взрослому."
            )
        elif choice_id == "share":
            lost = min(4, state.wallet)
            state.wallet -= lost
            state.feedback = (
                "Обещание оказалось ловушкой. Ты потерял "
                + str(lost)
                + " монет. Никому не отправляй секретные коды."
            )
        else:
            raise ValueError("Выбери, что сделать с сообщением")

    else:
        if amount is None or amount < 0 or amount > state.wallet:
            raise ValueError("Выбери сумму не больше остатка в кошельке")
        state.wallet -= amount
        state.dream += amount
        if amount >= min(4, episode.reserve_hint):
            state.score += 1
            state.feedback = (
                "Мечта стала ближе на " + str(amount) + " монет. Маленькие шаги работают."
            )
        else:
            state.feedback = (
                "Сегодня ты отложил " + str(amount) + " монет. Попробуй оставлять часть после нужд."
            )

    state.stage += 1
    return state


def medal(state: AdventureState) -> str:
    if state.score >= 4:
        return "Хранитель мечты"
    if state.score >= 2:
        return "Смелый исследователь"
    return "Новый маршрут"


def outcome(state: AdventureState) -> str:
    if state.care < 2:
        return (
            "Финик дошёл до цели, но ему не хватило заботы. В новом путешествии начни с еды и воды."
        )
    if state.dream < 4:
        return (
            "Финик полон сил. До большого окна ещё далеко: попробуй оставить часть монет для мечты."
        )
    if state.score >= 4:
        return (
            "Финик сыт и в безопасности. Ты предусмотрел неожиданность и приблизил большую мечту."
        )
    return "Финик сделал шаг к мечте. Подумай, какой выбор помог бы сохранить больше монет."
