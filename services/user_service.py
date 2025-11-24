from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import upsert_user, get_user, set_mode, set_active, set_proactive
from database.models import User


class UserService:
    """Сервис для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_or_update_user(self, tg_id: int, username: Optional[str]) -> User:
        return await upsert_user(self.session, tg_id, username)

    async def get_user(self, tg_id: int) -> Optional[User]:
        return await get_user(self.session, tg_id)

    async def update_mode(self, tg_id: int, mode: str) -> bool:
        return await set_mode(self.session, tg_id, mode)

    async def set_active(self, tg_id: int, active: bool) -> bool:
        return await set_active(self.session, tg_id, active)

    async def set_proactive(self, tg_id: int, enabled: bool) -> bool:
        return await set_proactive(self.session, tg_id, enabled)
