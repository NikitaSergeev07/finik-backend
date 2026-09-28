from pydantic import BaseModel, Field

from api.schemas.game import StateOut
from application.dto import GameState


class BonusIn(BaseModel):
    amount: int = Field(ge=1, le=20)
    reason: str = Field(min_length=1, max_length=80)
    pin: str = Field(min_length=1, max_length=16)


class BonusOut(BaseModel):
    amount: int
    reason: str
    state: StateOut

    @classmethod
    def from_state(cls, state: GameState, amount: int, reason: str) -> "BonusOut":
        return cls(amount=amount, reason=reason, state=StateOut.from_state(state))
