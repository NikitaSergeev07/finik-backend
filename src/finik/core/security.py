"""Токены устройства. Ребёнок ничего не вводит: телефон получает токен по device_id."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from finik.core.config import Settings
from finik.core.errors import Unauthorized

_ALGORITHM = "HS256"


def issue_token(player_id: UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(player_id),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_ttl_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def read_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
        return UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise Unauthorized("Токен недействителен, войди заново") from exc
