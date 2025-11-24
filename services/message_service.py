from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from services.message_history import MessageHistory


class MessageService:
    """Сервис для работы с сообщениями пользователей."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.history = MessageHistory(session)

    async def get_history(self, user: User) -> list[dict]:
        return await self.history.fetch(user)

    async def append_user_message(self, user: User, content: str) -> list[dict]:
        return await self.history.append_user_message(user, content)

    async def append_assistant_message(self, user: User, content: str) -> list[dict]:
        return await self.history.append_assistant_message(user, content)

    async def clear_history(self, tg_id: int) -> bool:
        return await self.history.clear(tg_id)

    async def get_last_message(self, user: User) -> dict | None:
        return await self.history.last_message(user)

    async def get_last_message_timestamp(self, user: User) -> float:
        return await self.history.last_message_timestamp(user)
