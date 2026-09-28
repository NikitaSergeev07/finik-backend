"""Сценарии ИИ: реплика, итог недели, слово дня, дневник, план мечты, чат.

Модель вызывается вне транзакции. Нет ключа или сбой — заготовленная фраза,
клиент ошибку не видит. Удачный ответ кладётся в кэш по ключу контекста.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from application import ai_prompts
from application.ports import LlmGateway, UnitOfWork
from application.use_cases._common import load_state
from core.errors import NotFound, RuleViolation
from domain import rules
from domain.entities import LogEntry
from domain.enums import ActionKind, Category, Mood
from domain.services import persona, safety, words
from domain.services import quiz as quiz_rules
from domain.services import shop as shop_rules


@dataclass(frozen=True, slots=True)
class AiText:
    text: str
    source: str
    mood: Mood | None = None
    week_number: int | None = None
    blocked: bool = False
    chat_left: int | None = None


@dataclass(frozen=True, slots=True)
class WordCard:
    word: str
    meaning: str
    example: str
    source: str


@dataclass(frozen=True, slots=True)
class DreamPlanView:
    title: str
    remain: int
    weekly_save: int
    weeks_left: int
    steps: list[tuple[str, int]]
    advice: str
    source: str
    cut_play: int = 0
    faster_save: int = 0
    weeks_saved: int = 0


@dataclass(frozen=True, slots=True)
class QuizView:
    kind: str
    source: str
    questions: list[quiz_rules.PriceQuestion]
    rewarded: bool


@dataclass(frozen=True, slots=True)
class QuizAnswerView:
    correct: bool
    explanation: str
    coins: int
    rewarded: bool
    already: bool


def _key(kind: str, *parts: object) -> str:
    raw = kind + ":" + ":".join(map(str, parts))
    return f"{kind}:{hashlib.sha256(raw.encode()).hexdigest()[:40]}"


def _read(payload: str | None) -> str | None:
    if not payload:
        return None
    try:
        return str(json.loads(payload)["text"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return payload


async def _complete(
    llm: LlmGateway,
    fallback: str,
    system: str,
    user: str,
    *,
    max_tokens: int,
    temperature: float,
    limit: int,
    sentences: int | None,
) -> tuple[str, str]:
    if not llm.enabled:
        return fallback, "fallback"
    raw = await llm.complete(
        system=system, user=user, max_tokens=max_tokens, temperature=temperature
    )
    if not raw:
        return fallback, "fallback"
    cleaned = safety.sanitize(raw, limit=limit, sentences=sentences)
    if not cleaned or safety.is_blocked(cleaned):
        return fallback, "fallback"
    return cleaned, "llm"


async def _remember(
    uow: UnitOfWork, key: str, text: str, *, player_id: UUID | None, kind: str
) -> None:
    async with uow:
        await uow.ai.put(
            key,
            json.dumps({"text": text}, ensure_ascii=False),
            player_id=player_id,
            kind=kind,
        )
        await uow.commit()


async def remark(uow: UnitOfWork, llm: LlmGateway, player_id: UUID) -> AiText:
    async with uow:
        state = await load_state(uow, player_id)
        fallback = persona.remark_fallback(state.pet, state.week, state.goal)
        key = _key(
            "remark",
            player_id,
            state.week.id,
            state.week.day,
            state.pet.mood,
            persona.lowest_need(state.pet),
        )
        cached = _read(await uow.ai.get(key)) if llm.enabled else None
        snap = ai_prompts.snapshot(state.player, state.pet, state.week, state.goal)
        system, user = ai_prompts.remark(state.pet.name, snap)
        mood = state.pet.mood
    if cached:
        return AiText(cached, "cache", mood=mood)
    text, source = await _complete(
        llm,
        fallback,
        system,
        user,
        max_tokens=80,
        temperature=0.8,
        limit=rules.AI_REMARK_CHARS,
        sentences=rules.AI_REMARK_SENTENCES,
    )
    if llm.enabled:
        await _remember(uow, key, text, player_id=player_id, kind="remark")
    return AiText(text, source, mood=mood)


async def week_summary(uow: UnitOfWork, llm: LlmGateway, player_id: UUID) -> AiText:
    async with uow:
        state = await load_state(uow, player_id)
        closed = await uow.weeks.list_closed(player_id, 1)
        if not closed:
            raise NotFound("Сначала доживи неделю до конца")
        week = closed[0]
        if week.summary_text:
            return AiText(week.summary_text, "cache", week_number=week.number)
        fallback = persona.week_summary_fallback(week, state.goal)
        snap = ai_prompts.snapshot(state.player, state.pet, week, state.goal)
        system, user = ai_prompts.week_story(state.pet.name, snap)
        number, week_id = week.number, week.id

    text, source = await _complete(
        llm,
        fallback,
        system,
        user,
        max_tokens=180,
        temperature=0.5,
        limit=rules.AI_STORY_CHARS,
        sentences=3,
    )
    async with uow:
        current = await uow.weeks.list_closed(player_id, 1)
        target = next((item for item in current if item.id == week_id), None)
        if target is not None and not target.summary_text:
            target.summary_text = text
            await uow.weeks.save(target)
            await uow.commit()
    return AiText(text, source, week_number=number)


async def word_of_day(uow: UnitOfWork, llm: LlmGateway, player_id: UUID) -> WordCard:
    today = datetime.now(UTC).date()
    async with uow:
        await load_state(uow, player_id)
        card = words.word_for_date(today)
        fallback = card.example
        key = _key("word", str(today), card.word)
        cached = _read(await uow.ai.get(key)) if llm.enabled else None
        system, user = ai_prompts.word_example("росток", card.word, card.meaning)
    if cached:
        return WordCard(card.word, card.meaning, cached, "cache")
    example, source = await _complete(
        llm,
        fallback,
        system,
        user,
        max_tokens=60,
        temperature=0.7,
        limit=180,
        sentences=1,
    )
    if llm.enabled:
        await _remember(uow, key, example, player_id=None, kind="word")
    return WordCard(card.word, card.meaning, example, source)


async def diary(uow: UnitOfWork, llm: LlmGateway, player_id: UUID) -> AiText:
    async with uow:
        state = await load_state(uow, player_id)
        entries = await uow.log.list_day(player_id, state.week.id, state.week.day)
        fallback = persona.diary_fallback(state.pet, state.week.day, entries)
        key = _key("diary", player_id, state.week.id, state.week.day)
        cached = _read(await uow.ai.get(key)) if llm.enabled else None
        snap = ai_prompts.snapshot(state.player, state.pet, state.week, state.goal)
        system, user = ai_prompts.diary(state.pet.name, snap, entries)
    if cached:
        return AiText(cached, "cache")
    text, source = await _complete(
        llm,
        fallback,
        system,
        user,
        max_tokens=160,
        temperature=0.7,
        limit=rules.AI_STORY_CHARS,
        sentences=3,
    )
    if llm.enabled:
        await _remember(uow, key, text, player_id=player_id, kind="diary")
    return AiText(text, source)


async def dream_plan(uow: UnitOfWork, llm: LlmGateway, player_id: UUID) -> DreamPlanView:
    async with uow:
        state = await load_state(uow, player_id)
        planned_save = state.week.entry(Category.SAVE).planned
        weekly_save = planned_save or max(1, state.week.income // 5)
        remain, weekly_save, steps = persona.dream_steps(state.goal, weekly_save)
        weeks_left = 0 if remain == 0 else (remain + weekly_save - 1) // weekly_save
        cut, faster, weeks_saved = persona.dream_speedup(
            state.week.entry(Category.PLAY).planned, remain, weekly_save
        )
        fallback = persona.dream_advice_fallback(
            state.goal, weekly_save, weeks_left, cut=cut, weeks_saved=weeks_saved
        )
        key = _key("dream", player_id, state.goal.id, state.goal.saved, weekly_save, cut)
        cached = _read(await uow.ai.get(key)) if llm.enabled else None
        snap = ai_prompts.snapshot(state.player, state.pet, state.week, state.goal)
        system, user = ai_prompts.dream_advice(
            state.pet.name, snap, remain, weekly_save, weeks_left, cut, faster, weeks_saved
        )
        title = state.goal.title
    if cached:
        return DreamPlanView(
            title, remain, weekly_save, weeks_left, steps, cached, "cache", cut, faster, weeks_saved
        )
    advice, source = await _complete(
        llm,
        fallback,
        system,
        user,
        max_tokens=120,
        temperature=0.4,
        limit=280,
        sentences=2,
    )
    if llm.enabled:
        await _remember(uow, key, advice, player_id=player_id, kind="dream")
    return DreamPlanView(
        title, remain, weekly_save, weeks_left, steps, advice, source, cut, faster, weeks_saved
    )


async def chat(uow: UnitOfWork, llm: LlmGateway, player_id: UUID, text: str) -> AiText:
    message = text.strip()
    if not message:
        raise RuleViolation("Напиши что-нибудь ростку")
    if len(message) > 300:
        message = message[:300]

    async with uow:
        state = await load_state(uow, player_id)
        if safety.is_blocked(message):
            return AiText(persona.REDIRECT, "fallback", mood=state.pet.mood, blocked=True)
        count_key = _key("chatcnt", player_id, state.week.id, state.week.day)
        used = int((await uow.ai.get(count_key)) or 0)
        left = max(0, rules.AI_CHAT_PER_DAY - used)
        if left <= 0:
            return AiText(persona.CHAT_TIRED, "fallback", mood=state.pet.mood, chat_left=0)
        await uow.ai.put(count_key, str(used + 1), player_id=player_id, kind="chatcnt")
        await uow.commit()
        snap = ai_prompts.snapshot(state.player, state.pet, state.week, state.goal)
        system, user = ai_prompts.chat(state.pet.name, snap, message)
        fallback = f"{state.pet.name} пока думает про копилку. Спроси про план или мечту."
        mood = state.pet.mood
        remaining = left - 1

    reply, source = await _complete(
        llm,
        fallback,
        system,
        user,
        max_tokens=120,
        temperature=0.7,
        limit=rules.AI_CHAT_CHARS,
        sentences=2,
    )
    return AiText(reply, source, mood=mood, chat_left=remaining)


async def origin(uow: UnitOfWork, llm: LlmGateway, player_id: UUID) -> AiText:
    async with uow:
        state = await load_state(uow, player_id)
        voice = persona.SPECIES_RU[state.pet.species]
        fallback = persona.origin_fallback(state.pet.species, state.pet.name)
        key = _key("origin", state.pet.species.value, state.pet.name.strip().lower())
        cached = _read(await uow.ai.get(key)) if llm.enabled else None
        system, user = ai_prompts.origin_story(state.pet.name, voice["title"], voice["trait"])
    if cached:
        return AiText(cached, "cache")
    text, source = await _complete(
        llm,
        fallback,
        system,
        user,
        max_tokens=280,
        temperature=0.6,
        limit=rules.AI_ORIGIN_CHARS,
        sentences=rules.AI_ORIGIN_SENTENCES,
    )
    if llm.enabled:
        await _remember(uow, key, text, player_id=None, kind="origin")
    return AiText(text, source)


def _quiz_kind(kind: str) -> str:
    return "riddle" if kind == "riddle" else "quiz"


def _questions_from_payload(payload: dict[str, object]) -> list[quiz_rules.PriceQuestion]:
    raw = list(payload.get("questions") or [])  # type: ignore[arg-type]
    out: list[quiz_rules.PriceQuestion] = []
    for index, item in enumerate(raw):
        row = dict(item)
        out.append(
            quiz_rules.PriceQuestion(
                index,
                str(row["question"]),
                list(row["options"]),
                int(row["right_index"]),
                str(row["explanation"]),
            )
        )
    return out


def _quiz_payload(
    questions: list[quiz_rules.PriceQuestion], answered: list[int], rewarded: bool
) -> str:
    body = {
        "questions": [
            {
                "question": q.question,
                "options": q.options,
                "right_index": q.right_index,
                "explanation": q.explanation,
            }
            for q in questions
        ],
        "answered": answered,
        "rewarded": rewarded,
    }
    return json.dumps(body, ensure_ascii=False)


async def get_quiz(
    uow: UnitOfWork, llm: LlmGateway, player_id: UUID, kind: str = "quiz"
) -> QuizView:
    kind = _quiz_kind(kind)
    async with uow:
        state = await load_state(uow, player_id)
        key = _key("quiz", player_id, state.week.id, state.week.day, kind)
        cached = await uow.ai.get(key)
        if cached:
            payload = json.loads(cached)
            questions = _questions_from_payload(payload)
            rewarded = bool(payload.get("rewarded"))
            return QuizView(kind, "cache", questions, rewarded)
        catalog = await uow.shop.list_items()
        priced = [
            shop_rules.with_week_price(item, state.week)
            for item in catalog
            if shop_rules.is_visible(item, state.player.unlocked_shop)
        ]
        seed = f"{state.week.id}:{state.week.day}:{kind}"
        questions = quiz_rules.build_questions(priced, kind, seed)
        if not questions:
            raise NotFound("В лавке мало товаров для вопроса")
        await uow.ai.put(
            key,
            _quiz_payload(questions, [], False),
            player_id=player_id,
            kind="quiz",
        )
        await uow.commit()
    return QuizView(kind, "fallback", questions, False)


async def answer_quiz(
    uow: UnitOfWork, player_id: UUID, index: int, answer_index: int, kind: str = "quiz"
) -> QuizAnswerView:
    kind = _quiz_kind(kind)
    async with uow:
        state = await load_state(uow, player_id)
        key = _key("quiz", player_id, state.week.id, state.week.day, kind)
        cached = await uow.ai.get(key)
        if not cached:
            raise NotFound("Сначала получи вопросы")
        payload = json.loads(cached)
        questions = _questions_from_payload(payload)
        if index < 0 or index >= len(questions):
            raise RuleViolation("Нет такого вопроса")
        answered = [int(i) for i in list(payload.get("answered") or [])]
        if index in answered:
            raise RuleViolation("На этот вопрос ты уже ответил")
        question = questions[index]
        correct = answer_index == question.right_index
        answered.append(index)
        coins = 0
        rewarded = bool(payload.get("rewarded"))
        if correct and not rewarded:
            coins = rules.QUIZ_REWARD
            state.player.free_coins += coins
            rewarded = True
            await uow.log.add(
                LogEntry(
                    player_id,
                    state.week.id,
                    state.week.day,
                    ActionKind.TASK_REWARD,
                    amount=coins,
                    note="Викторина по ценам лавки",
                    meta={"kind": kind, "index": index},
                )
            )
            await uow.players.save(state.player)
        await uow.ai.put(
            key,
            _quiz_payload(questions, answered, rewarded),
            player_id=player_id,
            kind="quiz",
        )
        await uow.commit()
        return QuizAnswerView(correct, question.explanation, coins, rewarded, False)
