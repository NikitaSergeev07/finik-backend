"""Перевод между строками базы и сущностями домена. Единственное место, где они встречаются."""

from domain.entities import (
    Badge,
    EventDef,
    EventInstance,
    EventOption,
    Goal,
    LogEntry,
    Pet,
    PlanEntry,
    Player,
    Purchase,
    QuizQuestion,
    ShopItem,
    TaskDef,
    TaskProgress,
    Week,
)
from domain.enums import Category, EventMode
from infrastructure.db.models import (
    ActionLogRow,
    BadgeDefRow,
    EventDefRow,
    EventInstanceRow,
    GoalRow,
    PetRow,
    PlanEntryRow,
    PlayerRow,
    PurchaseRow,
    QuizQuestionRow,
    ShopItemRow,
    TaskDefRow,
    TaskProgressRow,
    WeekRow,
)


def player_from_row(row: PlayerRow) -> Player:
    mode = row.event_mode if row.event_mode in {m.value for m in EventMode} else EventMode.RANDOM
    return Player(
        row.id,
        row.device_id,
        row.weekly_income,
        row.free_coins,
        row.sound_on,
        EventMode(mode),
        row.vaccinated_until,
        list(row.unlocked_shop or []),
    )


def player_to_row(player: Player, row: PlayerRow | None = None) -> PlayerRow:
    row = row or PlayerRow(id=player.id, device_id=player.device_id)
    row.weekly_income = player.weekly_income
    row.free_coins = player.free_coins
    row.sound_on = player.sound_on
    row.event_mode = str(player.event_mode)
    row.vaccinated_until = player.vaccinated_until
    row.unlocked_shop = list(player.unlocked_shop)
    return row


def pet_from_row(row: PetRow) -> Pet:
    needs = {
        Category.FOOD: row.need_food,
        Category.WATER: row.need_water,
        Category.PLAY: row.need_play,
    }
    return Pet(
        row.id,
        row.player_id,
        row.name,
        row.species,
        row.xp,
        needs,
        row.look_variant,
        row.equipped_pot or "",
        row.equipped_accessory or "",
    )


def pet_to_row(pet: Pet, row: PetRow | None = None) -> PetRow:
    row = row or PetRow(id=pet.id, player_id=pet.player_id, name=pet.name, species=pet.species)
    row.xp = pet.xp
    row.need_food = pet.needs[Category.FOOD]
    row.need_water = pet.needs[Category.WATER]
    row.need_play = pet.needs[Category.PLAY]
    row.look_variant = pet.look_variant
    row.equipped_pot = pet.equipped_pot
    row.equipped_accessory = pet.equipped_accessory
    return row


def week_from_row(row: WeekRow) -> Week:
    entries = {e.category: PlanEntry(e.category, e.planned, e.spent) for e in row.entries}
    for category in Category:  # старые недели без строки статьи не должны ломать домен
        entries.setdefault(category, PlanEntry(category, 0))
    return Week(
        row.id,
        row.player_id,
        row.number,
        row.income,
        row.day,
        entries,
        row.overrun,
        row.closed_at,
        row.summary_text,
        dict(row.modifiers or {}),
        bool(row.plan_confirmed),
    )


def week_to_row(week: Week, row: WeekRow | None = None) -> WeekRow:
    row = row or WeekRow(
        id=week.id, player_id=week.player_id, number=week.number, income=week.income
    )
    row.day = week.day
    row.overrun = week.overrun
    row.closed_at = week.closed_at
    row.summary_text = week.summary_text
    row.modifiers = dict(week.modifiers or {})
    row.plan_confirmed = week.plan_confirmed
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
    return Goal(
        row.id, row.player_id, row.title, row.target, row.saved, row.achieved_at, row.catalog_slug or ""
    )


def goal_to_row(goal: Goal, row: GoalRow | None = None) -> GoalRow:
    row = row or GoalRow(id=goal.id, player_id=goal.player_id)
    row.title, row.target, row.saved, row.achieved_at, row.catalog_slug = (
        goal.title,
        goal.target,
        goal.saved,
        goal.achieved_at,
        goal.catalog_slug,
    )
    return row


def log_from_row(row: ActionLogRow) -> LogEntry:
    return LogEntry(
        row.player_id,
        row.week_id,
        row.day,
        row.kind,
        row.amount,
        row.category,
        row.note,
        dict(row.meta or {}),
    )


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


def shop_item_from_row(row: ShopItemRow) -> ShopItem:
    return ShopItem(
        row.slug,
        row.name,
        row.category,
        row.cost,
        row.old_cost,
        row.glyph,
        row.restore,
        row.xp_bonus,
        hidden=bool(row.hidden),
        slot=row.slot or "",
    )


def purchase_to_row(p: Purchase) -> PurchaseRow:
    return PurchaseRow(
        id=p.id, player_id=p.player_id, week_id=p.week_id, item_slug=p.item_slug, cost=p.cost
    )


def task_def_from_row(row: TaskDefRow) -> TaskDef:
    return TaskDef(row.slug, row.title, row.kind, row.target, row.reward, dict(row.params))


def question_from_row(row: QuizQuestionRow) -> QuizQuestion:
    return QuizQuestion(
        row.slug,
        row.lesson_slug,
        row.order,
        row.question,
        list(row.options),
        row.right_index,
        row.explanation,
    )


def progress_from_row(row: TaskProgressRow) -> TaskProgress:
    return TaskProgress(
        row.player_id,
        row.week_id,
        row.task_slug,
        row.progress,
        dict(row.data),
        row.done_at,
        row.rewarded_at,
    )


def progress_to_row(p: TaskProgress, row: TaskProgressRow | None = None) -> TaskProgressRow:
    row = row or TaskProgressRow(player_id=p.player_id, week_id=p.week_id, task_slug=p.task_slug)
    row.progress, row.data, row.done_at, row.rewarded_at = (
        p.progress,
        dict(p.data),
        p.done_at,
        p.rewarded_at,
    )
    return row


def event_def_from_row(row: EventDefRow) -> EventDef:
    options = [
        EventOption(str(o["key"]), str(o["label"]), dict(o.get("effects", {}))) for o in row.options
    ]
    return EventDef(row.slug, row.title, row.text, row.weight, row.min_week, options)


def event_from_row(row: EventInstanceRow) -> EventInstance:
    return EventInstance(
        row.id, row.player_id, row.week_id, row.event_slug, row.day, row.chosen, row.resolved_at
    )


def event_to_row(e: EventInstance, row: EventInstanceRow | None = None) -> EventInstanceRow:
    row = row or EventInstanceRow(
        id=e.id, player_id=e.player_id, week_id=e.week_id, event_slug=e.event_slug, day=e.day
    )
    row.chosen, row.resolved_at = e.chosen, e.resolved_at
    return row


def badge_from_row(row: BadgeDefRow) -> Badge:
    return Badge(row.slug, row.name, row.note, dict(row.params))
