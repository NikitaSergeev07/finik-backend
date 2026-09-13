"""Что сценарии возвращают наружу. API превращает это в ответы, не заглядывая в домен."""

from dataclasses import dataclass

from domain.entities import Goal, Pet, Player, Week
from domain.services.care import CareOutcome
from domain.services.growth import DayOutcome, WeekOutcome


@dataclass(frozen=True, slots=True)
class GameState:
    player: Player
    pet: Pet
    week: Week
    goal: Goal


@dataclass(frozen=True, slots=True)
class CareResult:
    outcome: CareOutcome
    state: GameState


@dataclass(frozen=True, slots=True)
class DayResult:
    day: DayOutcome
    week: WeekOutcome | None
    state: GameState
