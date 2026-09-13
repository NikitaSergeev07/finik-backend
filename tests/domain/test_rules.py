"""Правила игры проверяются без базы и без HTTP."""

from uuid import uuid4

import pytest

from core.errors import RuleViolation
from domain import rules
from domain.entities import Goal, Pet, PlanEntry, Player, Week
from domain.enums import Category, Mood, Species
from domain.services import care, growth, planning


def make_world(income: int = 40, species: Species = Species.FINIK):
    pid = uuid4()
    player = Player(pid, "dev", income, free_coins=income)
    pet = Pet(
        uuid4(),
        pid,
        "Финик",
        species,
        xp=0,
        needs={c: rules.NEED_START for c in Category if c.is_need},
    )
    week = Week(uuid4(), pid, 1, income, day=1, entries={c: PlanEntry(c, 0) for c in Category})
    goal = Goal(uuid4(), pid, "Мечта", 150, 0)
    return player, pet, week, goal


def test_advised_plan_sums_to_income():
    for income in rules.INCOME_OPTIONS:
        assert sum(planning.advised_plan(income).values()) == income


def test_plan_cannot_exceed_budget():
    player, _, week, _ = make_world()
    with pytest.raises(RuleViolation):
        planning.apply_plan(
            player, week, {Category.FOOD: 41, Category.WATER: 0, Category.PLAY: 0, Category.SAVE: 0}
        )


def test_plan_moves_free_coins():
    player, _, week, _ = make_world()
    planning.apply_plan(player, week, planning.advised_plan(40))
    assert player.free_coins == 0
    assert week.planned_total == 40


def test_care_spends_from_category_and_restores_need():
    player, pet, week, _ = make_world()
    planning.apply_plan(player, week, planning.advised_plan(40))
    pet.needs[Category.WATER] = 50
    out = care.perform_care(pet, week, Category.WATER)
    assert out.cost == 2 and out.restored == 30
    assert week.entry(Category.WATER).spent == 2
    assert out.xp_gained == rules.XP_PER_CARE + rules.XP_CARE_TRAIT_BONUS  # Финик любит воду


def test_care_takes_from_savings_for_needs_only():
    player, pet, week, _ = make_world()
    planning.apply_plan(
        player, week, {Category.FOOD: 0, Category.WATER: 0, Category.PLAY: 0, Category.SAVE: 40}
    )
    out = care.perform_care(pet, week, Category.FOOD)
    assert out.from_savings and week.overrun == 3
    with pytest.raises(RuleViolation):
        care.perform_care(pet, week, Category.PLAY)


def test_mood_thresholds():
    assert rules.mood_for_needs([80, 80, 80]) is Mood.HAPPY
    assert rules.mood_for_needs([60, 60, 60]) is Mood.OKAY
    assert rules.mood_for_needs([40, 40, 40]) is Mood.BORED
    assert rules.mood_for_needs([10, 10, 10]) is Mood.SAD


def test_species_decay_differs():
    assert rules.decay_for(Species.FINIK, Category.WATER) > rules.decay_for(
        Species.CACTUS, Category.WATER
    )


def test_week_closes_into_goal_and_returns_leftovers():
    player, pet, week, goal = make_world()
    planning.apply_plan(player, week, planning.advised_plan(40))
    for _ in range(rules.DAYS_IN_WEEK):
        day = growth.end_day(pet, week)
    assert day.week_finished
    out = growth.close_week(player, pet, week, goal)
    assert goal.saved == 8 and out.saved == 8
    assert player.free_coins == 32  # ничего не тратили, всё вернулось
    assert pet.needs[Category.PLAY] == 0  # неделя без ухода


def test_stage_thresholds():
    assert rules.stage_for_xp(0) == 0
    assert rules.stage_for_xp(99) == 0
    assert rules.stage_for_xp(100) == 1
    assert rules.stage_for_xp(450) == 4
