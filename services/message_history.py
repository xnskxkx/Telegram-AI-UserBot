from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.time_utils import to_timestamp
from database.crud import append_history, clear_history, get_history
from database.models import User


class MessageHistory:
    """Обертка для работы с историей диалога пользователя."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch(self, user: User) -> list[dict]:
        """Получить историю сообщений."""
        return await get_history(self.session, user)

    async def append(self, user: User, role: str, content: str) -> list[dict]:
        """Добавить произвольное сообщение в историю."""
        return await append_history(self.session, user, role, content)

    async def append_user_message(self, user: User, content: str) -> list[dict]:
        return await self.append(user, "user", content)

    async def append_assistant_message(self, user: User, content: str) -> list[dict]:
        return await self.append(user, "assistant", content)

    async def clear(self, tg_id: int) -> bool:
        """Очистить историю пользователя."""
        return await clear_history(self.session, tg_id)

    async def last_message(self, user: User) -> dict | None:
        """Вернуть последнее сообщение из истории."""
        history = await self.fetch(user)
        return history[-1] if history else None

    async def last_message_timestamp(self, user: User) -> float:
        """Получить timestamp последней активности пользователя."""
        result = await self.session.execute(select(User).where(User.id == user.id))
        refreshed_user = result.scalar_one_or_none()

        if not refreshed_user or not refreshed_user.last_activity:
            return 0.0

        return to_timestamp(refreshed_user.last_activity)
