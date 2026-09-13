"""Достижения считаются по фактам, а не копятся флагами: проценты всегда честные."""

from dataclasses import dataclass

from domain import rules
from domain.entities import Badge, Goal, Pet, Week
from domain.enums import Category


@dataclass(frozen=True, slots=True)
class BadgeFacts:
    closed_weeks: list[Week]
    pet: Pet
    goal: Goal
    discount_purchases_total: int


def _streak(weeks: list[Week], ok) -> int:
    count = 0
    for week in reversed(weeks):
        if not ok(week):
            break
        count += 1
    return count


def percent_for(badge: Badge, facts: BadgeFacts) -> int:
    p = badge.params
    match badge.slug:
        case "plan_kept":
            need = int(p.get("weeks", 4))  # type: ignore[arg-type]
            return min(100, _streak(facts.closed_weeks, lambda w: w.overrun == 0) * 100 // need)
        case "twenty_percent":
            need = int(p.get("weeks", 4))  # type: ignore[arg-type]
            share = int(p.get("percent", 20))  # type: ignore[arg-type]

            def saved_enough(w: Week) -> bool:
                return w.income > 0 and w.entry(Category.SAVE).spent * 100 // w.income >= share

            return min(100, _streak(facts.closed_weeks, saved_enough) * 100 // need)
        case "sale_hunter":
            need = int(p.get("count", 10))  # type: ignore[arg-type]
            return min(100, facts.discount_purchases_total * 100 // need)
        case "halfway":
            return min(100, facts.goal.percent * 2)
        case "no_debt":
            return 100 if facts.closed_weeks and facts.closed_weeks[-1].overrun == 0 else 0
        case "big_tree":
            top = int(p.get("stage", len(rules.STAGE_THRESHOLDS) - 1))  # type: ignore[arg-type]
            return min(100, facts.pet.stage_index * 100 // top)
    return 0
