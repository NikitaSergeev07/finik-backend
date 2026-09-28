from fastapi import APIRouter

from api.deps import PlayerIdDep
from api.schemas.content import TermOut
from api.schemas.game import GoalCatalogOut
from domain import rules
from domain.services.words import WORDS

router = APIRouter(prefix="/content", tags=["Справочники"])


@router.get("/goals", response_model=list[GoalCatalogOut], summary="Каталог мечт")
async def goals(_player_id: PlayerIdDep) -> list[GoalCatalogOut]:
    """Три цели на выбор: название, цена и короткое «зачем»."""
    return [
        GoalCatalogOut(slug=g.slug, title=g.title, target=g.target, why=g.why)
        for g in rules.GOAL_CATALOG
    ]


@router.get("/terms", response_model=list[TermOut], summary="Словарь")
async def terms(_player_id: PlayerIdDep) -> list[TermOut]:
    return [TermOut(word=w.word, meaning=w.meaning, example=w.example) for w in WORDS]
