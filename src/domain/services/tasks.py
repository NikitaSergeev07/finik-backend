"""Оценка заданий по фактам недели. Факты собирает сценарий, правило только считает."""

from dataclasses import dataclass, replace

from domain import rules
from domain.entities import TaskDef, Week
from domain.enums import Category, TaskKind, TaskTarget


@dataclass(frozen=True, slots=True)
class WeekFacts:
    """Всё, что нужно знать о неделе, чтобы оценить любое задание."""

    week: Week
    quiz_correct: int
    quiz_total: int
    care_days: int
    discount_purchases: int
    deposits: int
    week_closed: bool
    need_purchases: int = 0


@dataclass(frozen=True, slots=True)
class TaskStatus:
    progress: int
    goal: int
    done: bool
    subtitle: str


def scale_task(task: TaskDef, week_number: int) -> TaskDef:
    """Цели и награды растут с номером недели. Оценка идёт уже по этим числам."""
    params = dict(task.params)
    reward = rules.scaled_task_reward(task.reward, week_number)
    title = task.title
    if "amount" in params:
        amount = rules.scaled_task_amount(int(params["amount"]), week_number)
        params["amount"] = amount
        title = f"Отложи {amount} монет до конца недели"
    if task.slug == "food_plan" and week_number >= rules.WEEK_TASK_STRICT_FROM:
        params["no_overrun"] = True
        title = "Уложись в план по еде и без перерасхода"
    return replace(task, title=title, reward=reward, params=params)


def evaluate(task: TaskDef, facts: WeekFacts) -> TaskStatus:
    match (task.kind, task.target):
        case (TaskKind.LESSON, _):
            total = max(facts.quiz_total, 1)
            return TaskStatus(
                facts.quiz_correct,
                total,
                facts.quiz_correct >= total,
                f"{facts.quiz_correct} из {total} шагов",
            )
        case (TaskKind.WEEK, TaskTarget.GOAL):
            need = int(task.params.get("amount", 10))
            saved = facts.deposits + facts.week.entry(Category.SAVE).left
            days_left = max(0, 7 - facts.week.day + 1)
            return TaskStatus(min(saved, need), need, saved >= need, f"осталось {days_left} дн.")
        case (TaskKind.WEEK, TaskTarget.PLAN):
            category = Category(str(task.params.get("category", "FOOD")))
            entry = facts.week.entry(category)
            done = facts.week_closed and entry.spent <= entry.planned
            if bool(task.params.get("no_overrun")):
                done = done and facts.week.overrun == 0
            return TaskStatus(
                entry.spent, entry.planned, done, f"потрачено {entry.spent} из {entry.planned}"
            )
        case (TaskKind.HABIT, _):
            days = int(task.params.get("days", 7))
            return TaskStatus(
                min(facts.care_days, days),
                days,
                facts.care_days >= days,
                f"{facts.care_days} из {days}",
            )
        case (TaskKind.DAY, TaskTarget.SHOP):
            count = int(task.params.get("count", 1))
            if task.params.get("need"):
                done = facts.need_purchases >= count
                return TaskStatus(
                    min(facts.need_purchases, count),
                    count,
                    done,
                    "купи обязательное: еду или воду",
                )
            return TaskStatus(
                min(facts.discount_purchases, count),
                count,
                facts.discount_purchases >= count,
                "в лавке есть скидки",
            )
    return TaskStatus(0, 1, False, "")
