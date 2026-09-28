"""Событие дня: одно на игровой день, выбор применяется один раз."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import NotFound, RuleViolation
from domain.entities import EventDef, EventInstance, LogEntry
from domain.enums import ActionKind
from domain.services import events as event_rules


@dataclass(frozen=True, slots=True)
class EventView:
    instance: EventInstance
    definition: EventDef


@dataclass(frozen=True, slots=True)
class ChoiceResult:
    outcome: event_rules.EventOutcome
    state: GameState


async def today(uow: UnitOfWork, player_id: UUID) -> EventView | None:
    async with uow:
        state = await load_state(uow, player_id)
        week = state.week
        instance = await uow.events.get_for_day(player_id, week.id, week.day)
        if instance is None:
            seed = f"{player_id}:{week.number}:{week.day}"
            definition = event_rules.pick_event(
                await uow.events.list_defs(),
                week.number,
                seed,
                mode=state.player.event_mode,
                blocked=event_rules.blocked_slugs(state.player, week.number),
            )
            if definition is None:
                return None
            instance = EventInstance(uuid4(), player_id, week.id, definition.slug, week.day)
            await uow.events.add(instance)
            await uow.commit()
        else:
            definition = await uow.events.get_def(instance.event_slug)
            if definition is None:
                return None
        return EventView(instance, definition)


async def choose(uow: UnitOfWork, player_id: UUID, instance_id: UUID, key: str) -> ChoiceResult:
    async with uow:
        state = await load_state(uow, player_id)
        instance = await uow.events.get(instance_id)
        if instance is None or instance.player_id != player_id:
            raise NotFound("Событие не найдено")
        if instance.resolved_at is not None:
            raise RuleViolation("Выбор уже сделан")
        if instance.week_id != state.week.id or instance.day != state.week.day:
            raise RuleViolation("Это событие уже прошло")
        definition = await uow.events.get_def(instance.event_slug)
        option = definition.option(key) if definition else None
        if definition is None or option is None:
            raise NotFound("Такого варианта нет")

        outcome = event_rules.apply_option(state.player, state.pet, state.week, option)
        instance.chosen = key
        instance.resolved_at = _now()
        await uow.events.save(instance)
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.EVENT_CHOICE,
                amount=outcome.coins_delta,
                note=f"{definition.title}: {option.label}",
                meta={"slug": definition.slug, "option": key, "xp": outcome.xp_delta},
            )
        )
        await uow.players.save(state.player)
        await uow.pets.save(state.pet)
        await uow.weeks.save(state.week)
        await uow.commit()
        return ChoiceResult(outcome, state)


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
