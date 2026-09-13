from fastapi import APIRouter

from finik.api.v1 import auth, game

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(game.router)
