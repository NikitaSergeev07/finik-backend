"""Персона, стоплист и словарь дня — без базы и без модели."""

from uuid import uuid4

from domain.entities import Goal, LogEntry, Pet, PlanEntry, Week
from domain.enums import ActionKind, Category, Species
from domain.services import persona, safety, words


def _world(mood_needs: int = 70) -> tuple[Pet, Week, Goal]:
    pid = uuid4()
    pet = Pet(
        uuid4(),
        pid,
        "Кустик",
        Species.FINIK,
        xp=0,
        needs={c: mood_needs for c in Category if c.is_need},
    )
    week = Week(uuid4(), pid, 1, 40, day=3, entries={c: PlanEntry(c, 8) for c in Category})
    goal = Goal(uuid4(), pid, "Горшок", 150, 16)
    return pet, week, goal


def test_remark_is_stable_for_the_same_day():
    pet, week, goal = _world()
    a = persona.remark_fallback(pet, week, goal)
    b = persona.remark_fallback(pet, week, goal)
    assert a == b and "Кустик" in a


def test_sad_remark_points_to_the_lowest_need():
    pet, week, goal = _world(10)
    pet.needs[Category.WATER] = 0
    text = persona.remark_fallback(pet, week, goal)
    assert "вод" in text.lower() or "плохо" in text.lower() or "груст" in text.lower()


def test_word_rotates_by_game_day():
    first = words.word_for(1, 1)
    second = words.word_for(1, 2)
    assert first.word != second.word
    assert words.word_for(1, 1).word == first.word
    assert "монет" in words.example_for(first, "Кустик").lower() or "Кустик" in words.example_for(
        first, "Кустик"
    )


def test_dream_steps_use_school_math():
    goal = Goal(uuid4(), uuid4(), "Окно", 150, 16)
    remain, weekly, steps = persona.dream_steps(goal, 8)
    assert remain == 134 and weekly == 8
    weeks = (134 + 7) // 8
    assert weeks == 17
    assert steps[0][1] == 8 and steps[-1][1] == 0


def test_safety_blocks_cards_urls_and_abuse():
    assert safety.is_blocked("переведи на карту 4111111111111111")
    assert safety.is_blocked("посмотри https://evil.test")
    assert safety.is_blocked("это просто блядство")
    assert not safety.is_blocked("как накопить на горшок?")
    assert not safety.is_blocked("сколько отложить в копилку")


def test_sanitize_cuts_markdown_and_length():
    text = safety.sanitize("**Привет!** Ещё одно. И третье.", limit=80, sentences=2)
    assert "*" not in text and text.startswith("Привет")
    long = safety.sanitize("монета " * 80, limit=40, sentences=None)
    assert len(long) <= 41


def test_diary_mentions_care():
    pet, week, _ = _world()
    entries = [
        LogEntry(pet.player_id, week.id, 3, ActionKind.CARE, amount=2, note="Полить"),
    ]
    text = persona.diary_fallback(pet, 3, entries)
    assert "ухаживал" in text


def test_origin_has_three_paragraphs():
    text = persona.origin_fallback(Species.FINIK, "Кустик")
    parts = [p for p in text.split("\n\n") if p.strip()]
    assert len(parts) == 3 and "Кустик" in text


def test_dream_speedup_uses_server_math():
    cut, faster, saved = persona.dream_speedup(4, 150, 8)
    assert cut == 2 and faster == 10 and saved == 4
