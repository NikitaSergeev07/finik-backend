"""Правила недельного плана: доход раскладывается по статьям, не больше доступного."""

from core.errors import RuleViolation
from domain import rules
from domain.entities import PlanEntry, Player, Week
from domain.enums import Category


def available_for_plan(player: Player, week: Week) -> int:
    """Свободные монеты плюс то, что уже заложено, но ещё не потрачено."""
    unspent = sum(entry.left for entry in week.entries.values())
    return player.free_coins + unspent


def apply_plan(player: Player, week: Week, planned: dict[Category, int]) -> None:
    """Переложить нераспределённые монеты по статьям. Потраченное не трогаем."""
    for category in Category:
        if category not in planned:
            raise RuleViolation(f"Не указана статья «{category}»")
        if planned[category] < 0:
            raise RuleViolation("Сумма по статье не может быть отрицательной")
        if planned[category] < week.entry(category).spent:
            raise RuleViolation(
                f"По статье «{category}» уже потрачено {week.entry(category).spent}, "
                "меньше заложить нельзя"
            )

    total = sum(planned.values())
    # Planned totals include money already spent; using only unspent loses coins.
    budget = player.free_coins + week.planned_total
    if total > budget:
        raise RuleViolation(f"Можно распределить не больше {budget} монет, а в плане {total}")

    for category, amount in planned.items():
        week.entries[category] = PlanEntry(category, amount, week.entry(category).spent)
    player.free_coins = budget - total


def advised_plan(income: int) -> dict[Category, int]:
    """Совет 40/30/10/20. Остаток от округления уходит в копилку."""
    plan = {cat: income * share // 100 for cat, share in rules.ADVICE_SHARES.items()}
    plan[Category.SAVE] += income - sum(plan.values())
    return plan
