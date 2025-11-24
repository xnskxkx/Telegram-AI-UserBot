from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import append_history, get_history, clear_history
from database.models import User


class MessageService:
    """Сервис для работы с сообщениями пользователей."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_history(self, user: User) -> list[dict]:
        return await get_history(self.session, user)

    async def append_user_message(self, user: User, content: str) -> list[dict]:
        return await append_history(self.session, user, "user", content)

    async def append_assistant_message(self, user: User, content: str) -> list[dict]:
        return await append_history(self.session, user, "assistant", content)

    async def clear_history(self, tg_id: int) -> bool:
        return await clear_history(self.session, tg_id)
