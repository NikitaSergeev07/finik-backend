from fastapi import APIRouter

from api.v1 import auth, events, game, history, profile, shop, tasks, ai, quiz

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(game.router)
api_router.include_router(shop.router)
api_router.include_router(tasks.router)
api_router.include_router(history.router)
api_router.include_router(events.router)
api_router.include_router(profile.router)
api_router.include_router(ai.router)
api_router.include_router(quiz.router)
