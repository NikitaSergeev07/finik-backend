"""Зависимости FastAPI: настройки, единица работы, текущий игрок по токену."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.ports import LlmGateway, UnitOfWork
from core.config import Settings, get_settings
from core.errors import Unauthorized
from core.security import read_token
from infrastructure.ai.gateway import SilentLlm
from infrastructure.db.engine import get_session_factory
from infrastructure.db.uow import SqlAlchemyUnitOfWork

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_uow() -> UnitOfWork:
    return SqlAlchemyUnitOfWork(get_session_factory())


UowDep = Annotated[UnitOfWork, Depends(get_uow)]


_bearer = HTTPBearer(auto_error=False, description="Токен из POST /auth/device")


def current_player_id(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> UUID:
    if credentials is None:
        raise Unauthorized("Нужен токен устройства")
    return read_token(credentials.credentials, settings)


PlayerIdDep = Annotated[UUID, Depends(current_player_id)]


def get_llm(request: Request) -> LlmGateway:
    return getattr(request.app.state, "llm", SilentLlm())


LlmDep = Annotated[LlmGateway, Depends(get_llm)]
