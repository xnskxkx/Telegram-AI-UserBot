import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from .models import User, Dialog
from config import CONTEXT_MAX_TURNS
from datetime import datetime

async def upsert_user(session: AsyncSession, tg_id: int, username: Optional[str]) -> User:
    """Создать или обновить пользователя"""
    try:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()

        if user is None:
            user = User(tg_id=tg_id, username=username, mode="normal", active=True)
            session.add(user)
            await session.flush()

            # Создаём пустую историю диалога
            dialog = Dialog(user_id=user.id, history_json="[]")
            session.add(dialog)
            await session.commit()
        else:
            # Обновляем username если изменился
            if user.username != username:
                user.username = username
                await session.commit()

        return user
    except SQLAlchemyError as e:
        await session.rollback()
        raise e

async def get_user(session: AsyncSession, tg_id: int) -> Optional[User]:
    """Получить пользователя по tg_id"""
    res = await session.execute(select(User).where(User.tg_id == tg_id))
    return res.scalar_one_or_none()

async def set_mode(session: AsyncSession, tg_id: int, mode: str) -> bool:
    """Установить режим общения"""
    try:
        user = await get_user(session, tg_id)
        if not user:
            return False
        user.mode = mode
        await session.commit()
        return True
    except SQLAlchemyError:
        await session.rollback()
        return False

async def set_active(session: AsyncSession, tg_id: int, active: bool) -> bool:
    """Включить/выключить ответы пользователю"""
    try:
        user = await get_user(session, tg_id)
        if not user:
            return False
        user.active = active
        await session.commit()
        return True
    except SQLAlchemyError:
        await session.rollback()
        return False

async def set_proactive(session: AsyncSession, tg_id: int, enabled: bool) -> bool:
    user = await get_user(session, tg_id)
    if not user:
        return False
    user.proactive_enabled = enabled
    await session.commit()
    return True

async def get_or_create_dialog(session: AsyncSession, user: User) -> Dialog:
    """Получить или создать диалог для пользователя"""
    res = await session.execute(select(Dialog).where(Dialog.user_id == user.id))
    dialog = res.scalar_one_or_none()

    if dialog is None:
        dialog = Dialog(user_id=user.id, history_json="[]")
        session.add(dialog)
        await session.flush()

    return dialog

async def append_history(session: AsyncSession, user: User, role: str, content: str) -> list[dict]:
    """Добавить сообщение в историю диалога"""
    try:
        dialog = await get_or_create_dialog(session, user)

        # Парсим существующую историю
        try:
            hist = json.loads(dialog.history_json)
        except json.JSONDecodeError:
            hist = []

        # Добавляем новое сообщение
        hist.append({"role": role, "content": content})

        if role == "user":
            user.last_activity = datetime.utcnow()

        # Обрезаем до последних CONTEXT_MAX_TURNS*2 сообщений
        if len(hist) > CONTEXT_MAX_TURNS * 2:
            hist = hist[-CONTEXT_MAX_TURNS * 2:]

        # Сохраняем обратно
        dialog.history_json = json.dumps(hist, ensure_ascii=False)
        await session.commit()

        return hist
    except SQLAlchemyError as e:
        await session.rollback()
        raise e

async def get_history(session: AsyncSession, user: User) -> list[dict]:
    """Получить историю диалога"""
    dialog = await get_or_create_dialog(session, user)

    try:
        return json.loads(dialog.history_json)
    except json.JSONDecodeError:
        return []

async def clear_history(session: AsyncSession, tg_id: int) -> bool:
    """Очистить историю диалога пользователя"""
    try:
        user = await get_user(session, tg_id)
        if not user:
            return False

        dialog = await get_or_create_dialog(session, user)
        dialog.history_json = "[]"
        await session.commit()
        return True
    except SQLAlchemyError:
        await session.rollback()
        return False
