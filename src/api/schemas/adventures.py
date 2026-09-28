"""Public state for interactive financial story missions."""

from pydantic import BaseModel, Field

from domain.services.adventure import STAGES, AdventureState, Episode, medal, outcome, scene


class AdventureActionIn(BaseModel):
    expected_stage: int = Field(ge=0, le=STAGES)
    food: int | None = Field(default=None, ge=0, le=100)
    water: int | None = Field(default=None, ge=0, le=100)
    reserve: int | None = Field(default=None, ge=0, le=100)
    choice_id: str | None = None
    amount: int | None = Field(default=None, ge=0, le=100)


class AdventureOut(BaseModel):
    slug: str
    title: str
    summary: str
    stage: int
    total: int
    wallet: int
    reserve: int
    care: int
    joy: int
    score: int
    dream: int
    feedback: str
    pet_reaction: str = ""
    completed: bool
    rewarded: bool
    medal: str | None
    outcome: str
    scene: dict[str, object]

    @classmethod
    def from_state(
        cls, episode: Episode, state: AdventureState, rewarded: bool, pet_reaction: str = ""
    ) -> "AdventureOut":
        return cls(
            slug=episode.slug,
            title=episode.title,
            summary=episode.summary,
            stage=state.stage,
            total=STAGES,
            wallet=state.wallet,
            reserve=state.reserve,
            care=state.care,
            joy=state.joy,
            score=state.score,
            dream=state.dream,
            feedback=state.feedback,
            pet_reaction=pet_reaction,
            completed=state.stage == STAGES,
            rewarded=rewarded,
            medal=medal(state) if state.stage == STAGES else None,
            outcome=outcome(state) if state.stage == STAGES else "",
            scene=scene(episode, state),
        )
