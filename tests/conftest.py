"""Тесты API идут на отдельной базе finik_test: схема создаётся заново на каждую сессию."""

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("FINIK_DATABASE_URL", "postgresql+asyncpg://localhost:5432/finik_test")

from finik.infrastructure.db import models  # noqa: F401
from finik.infrastructure.db.base import Base
from finik.infrastructure.db.engine import get_engine
from finik.main import create_app


@pytest.fixture(scope="session", autouse=True)
async def _schema() -> AsyncIterator[None]:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
