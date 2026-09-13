"""Перевод между строками базы и сущностями домена. Единственное место, где они встречаются."""

from domain.entities import Goal, LogEntry, Pet, PlanEntry, Player, Week
from domain.enums import Category
from infrastructure.db.models import (
    ActionLogRow,
    GoalRow,
    PetRow,
    PlanEntryRow,
    PlayerRow,
    WeekRow,
)


def player_from_row(row: PlayerRow) -> Player:
    return Player(row.id, row.device_id, row.weekly_income, row.free_coins, row.sound_on)


def player_to_row(player: Player, row: PlayerRow | None = None) -> PlayerRow:
    row = row or PlayerRow(id=player.id, device_id=player.device_id)
    row.weekly_income = player.weekly_income
    row.free_coins = player.free_coins
    row.sound_on = player.sound_on
    return row


def pet_from_row(row: PetRow) -> Pet:
    needs = {
        Category.FOOD: row.need_food,
        Category.WATER: row.need_water,
        Category.PLAY: row.need_play,
    }
    return Pet(row.id, row.player_id, row.name, row.species, row.xp, needs)


def pet_to_row(pet: Pet, row: PetRow | None = None) -> PetRow:
    row = row or PetRow(id=pet.id, player_id=pet.player_id, name=pet.name, species=pet.species)
    row.xp = pet.xp
    row.need_food = pet.needs[Category.FOOD]
    row.need_water = pet.needs[Category.WATER]
    row.need_play = pet.needs[Category.PLAY]
    return row


def week_from_row(row: WeekRow) -> Week:
    entries = {e.category: PlanEntry(e.category, e.planned, e.spent) for e in row.entries}
    for category in Category:  # старые недели без строки статьи не должны ломать домен
        entries.setdefault(category, PlanEntry(category, 0))
    return Week(
        row.id, row.player_id, row.number, row.income, row.day, entries, row.overrun, row.closed_at
    )


def week_to_row(week: Week, row: WeekRow | None = None) -> WeekRow:
    row = row or WeekRow(
        id=week.id, player_id=week.player_id, number=week.number, income=week.income
    )
    row.day = week.day
    row.overrun = week.overrun
    row.closed_at = week.closed_at
    existing = {e.category: e for e in row.entries}
    for category, entry in week.entries.items():
        target = existing.get(category)
        if target is None:
            row.entries.append(
                PlanEntryRow(category=category, planned=entry.planned, spent=entry.spent)
            )
        else:
            target.planned, target.spent = entry.planned, entry.spent
    return row


def goal_from_row(row: GoalRow) -> Goal:
    return Goal(row.id, row.player_id, row.title, row.target, row.saved, row.achieved_at)


def goal_to_row(goal: Goal, row: GoalRow | None = None) -> GoalRow:
    row = row or GoalRow(id=goal.id, player_id=goal.player_id)
    row.title, row.target, row.saved, row.achieved_at = (
        goal.title,
        goal.target,
        goal.saved,
        goal.achieved_at,
    )
    return row


def log_to_row(entry: LogEntry) -> ActionLogRow:
    return ActionLogRow(
        player_id=entry.player_id,
        week_id=entry.week_id,
        day=entry.day,
        kind=entry.kind,
        category=entry.category,
        amount=entry.amount,
        note=entry.note,
        meta=entry.meta,
    )
