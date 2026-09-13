from fastapi import APIRouter

from api.v1 import auth, game, history, shop, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(game.router)
api_router.include_router(shop.router)
api_router.include_router(tasks.router)
api_router.include_router(history.router)
