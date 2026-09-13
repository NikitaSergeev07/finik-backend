"""Уход за ростком: действие стоит монет из своей статьи и восстанавливает потребность."""

from dataclasses import dataclass

from finik.core.errors import RuleViolation
from finik.domain import rules
from finik.domain.entities import Pet, Week
from finik.domain.enums import Category


@dataclass(frozen=True, slots=True)
class CareOutcome:
    category: Category
    cost: int
    restored: int
    xp_gained: int
    from_savings: bool


def perform_care(pet: Pet, week: Week, category: Category) -> CareOutcome:
    if not category.is_need:
        raise RuleViolation("Из копилки ухаживать нельзя, она только на мечту")
    action = rules.CARE_ACTIONS[category]
    entry = week.entry(category)
    from_savings = False

    if entry.left >= action.cost:
        entry.spent += action.cost
    elif category is not Category.PLAY and week.entry(Category.SAVE).left >= action.cost:
        # Еда и вода важнее копилки: берём оттуда, но это перерасход и он запоминается.
        week.entry(Category.SAVE).spent += action.cost
        week.overrun += action.cost
        from_savings = True
    else:
        raise RuleViolation(f"В статье «{action.label}» нет монет. Загляни в план недели")

    before = pet.needs[category]
    pet.needs[category] = min(rules.NEED_MAX, before + action.restore)
    xp = rules.XP_PER_CARE
    if rules.SPECIES_TRAITS[pet.species].bonus_category is category:
        xp += rules.XP_CARE_TRAIT_BONUS
    pet.xp += xp
    return CareOutcome(category, action.cost, pet.needs[category] - before, xp, from_savings)
