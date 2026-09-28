"""Викторина по ценам: верный индекс считает сервер."""

from domain.entities import ShopItem
from domain.enums import Category
from domain.services.quiz import build_questions


def _shelf() -> list[ShopItem]:
    return [
        ShopItem("ball", "Мячик", Category.PLAY, 3, 5, "C", 0, 0),
        ShopItem("food_week", "Корм", Category.FOOD, 12, None, "P", 0, 0),
        ShopItem("water_3d", "Вода", Category.WATER, 3, None, "W", 0, 0),
    ]


def test_quiz_answers_match_shop_math():
    questions = build_questions(_shelf(), "quiz", "seed-a")
    assert 1 <= len(questions) <= 3
    sale = next(q for q in questions if "%" in q.options[0] or any("%" in o for o in q.options))
    # мячик 3 из 5 → 40%
    assert sale.options[sale.right_index] == "40%"
    how = next(q for q in questions if "шт." in q.options[0])
    # 12 // 3 = 4
    assert how.options[how.right_index] == "4 шт."


def test_riddle_uses_same_numbers():
    quiz = build_questions(_shelf(), "quiz", "seed-b")
    riddle = build_questions(_shelf(), "riddle", "seed-b")
    assert [q.right_index for q in quiz] == [q.right_index for q in riddle]
    assert quiz[0].question != riddle[0].question
