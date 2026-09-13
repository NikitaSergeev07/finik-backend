from fastapi import APIRouter

from api.deps import PlayerIdDep, UowDep
from api.schemas.content import BuyIn, PurchaseOut, ShopItemOut
from application.use_cases import shop

router = APIRouter(prefix="/shop", tags=["Лавка"])


@router.get("/items", response_model=list[ShopItemOut], summary="Витрина лавки")
async def items(player_id: PlayerIdDep, uow: UowDep) -> list[ShopItemOut]:
    """Для каждого товара: сколько осталось в его статье и хватает ли на покупку."""
    return [ShopItemOut.from_shelf(s) for s in await shop.list_shelf(uow, player_id)]


@router.post("/buy", response_model=PurchaseOut, summary="Купить товар")
async def buy(body: BuyIn, player_id: PlayerIdDep, uow: UowDep) -> PurchaseOut:
    """Списывается из статьи товара. Если в статье пусто, покупка не проходит."""
    return PurchaseOut.from_result(await shop.buy(uow, player_id, body.slug))
