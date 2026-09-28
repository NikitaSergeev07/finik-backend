"""Премия от родителя: ребёнок сам себе монеты не начисляет."""

import secrets
from uuid import UUID

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from core.errors import RuleViolation
from domain import rules
from domain.entities import LogEntry
from domain.enums import ActionKind


def pin_matches(given: str, expected: str) -> bool:
    left, right = given.encode(), expected.encode()
    if len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


async def grant_bonus(
    uow: UnitOfWork, player_id: UUID, amount: int, reason: str, pin: str, expected_pin: str
) -> GameState:
    if not pin_matches(pin, expected_pin):
        raise RuleViolation("Неверный код родителя")
    if not rules.PARENT_BONUS_MIN <= amount <= rules.PARENT_BONUS_MAX:
        raise RuleViolation(
            f"Премия бывает от {rules.PARENT_BONUS_MIN} до {rules.PARENT_BONUS_MAX} монет"
        )
    note = reason.strip() or "Премия за дело"
    if len(note) > 80:
        note = note[:80]
    async with uow:
        state = await load_state(uow, player_id)
        state.player.free_coins += amount
        await uow.log.add(
            LogEntry(
                player_id,
                state.week.id,
                state.week.day,
                ActionKind.PARENT_BONUS,
                amount=amount,
                note=note,
                meta={"reason": note},
            )
        )
        await uow.players.save(state.player)
        await uow.commit()
        return state
