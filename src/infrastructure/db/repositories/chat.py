from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.db.models import ChatMessageModel

class SqlAlchemyChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_recent_messages(self, player_id: UUID, limit: int = 20) -> list[ChatMessageModel]:
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.player_id == player_id)
            .order_by(ChatMessageModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.scalars(stmt)
        # Возвращаем сообщения в хронологическом порядке (от старых к новым)
        return list(reversed(result.all()))

    async def add_message(self, player_id: UUID, role: str, content: str) -> ChatMessageModel:
        message = ChatMessageModel(
            player_id=player_id,
            role=role,
            content=content,
        )
        self._session.add(message)
        return message