"""Зависимости FastAPI: настройки, единица работы, текущий игрок по токену."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from application.ports import UnitOfWork
from core.config import Settings, get_settings
from core.errors import Unauthorized
from core.security import read_token
from infrastructure.db.engine import get_session_factory
from infrastructure.db.uow import SqlAlchemyUnitOfWork

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_uow() -> UnitOfWork:
    return SqlAlchemyUnitOfWork(get_session_factory())


UowDep = Annotated[UnitOfWork, Depends(get_uow)]


def current_player_id(
    settings: SettingsDep, authorization: Annotated[str | None, Header()] = None
) -> UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Нужен токен устройства")
    return read_token(authorization.split(" ", 1)[1].strip(), settings)


PlayerIdDep = Annotated[UUID, Depends(current_player_id)]
