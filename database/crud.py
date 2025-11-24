import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from .models import User, Dialog
from config import CONTEXT_MAX_TURNS
from datetime import datetime


async def _cleanup_transaction(session: AsyncSession, success: bool):
    """Откатывает незавершённые транзакции, если операция завершилась неуспешно."""
    if success:
        return
    try:
        if session.in_transaction():
            await session.rollback()
    except SQLAlchemyError:
        # Если откат не удался, логика вызывающей стороны обработает состояние сессии
        pass



async def upsert_user(session: AsyncSession, tg_id: int, username: Optional[str]) -> User:
    """Создать или обновить пользователя"""
    success = False
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

        success = True
        return user
    except SQLAlchemyError as e:
        await session.rollback()
        raise e
    finally:
        await _cleanup_transaction(session, success)


async def get_user(session: AsyncSession, tg_id: int) -> Optional[User]:
    """Получить пользователя по tg_id"""
    success = False
    try:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        success = True
        return user
    except SQLAlchemyError:
        await session.rollback()
        return None
    finally:
        await _cleanup_transaction(session, success)


async def set_mode(session: AsyncSession, tg_id: int, mode: str) -> bool:
    """Установить режим общения"""
    success = False
    try:
        user = await get_user(session, tg_id)
        if not user:
            return False
        user.mode = mode
        await session.commit()
        success = True
        return True
    except SQLAlchemyError:
        await session.rollback()
        return False
    finally:
        await _cleanup_transaction(session, success)


async def set_active(session: AsyncSession, tg_id: int, active: bool) -> bool:
    """Включить/выключить ответы пользователю"""
    success = False
    try:
        user = await get_user(session, tg_id)
        if not user:
            return False
        user.active = active
        await session.commit()
        success = True
        return True
    except SQLAlchemyError:
        await session.rollback()
        return False
    finally:
        await _cleanup_transaction(session, success)


async def set_proactive(session: AsyncSession, tg_id: int, enabled: bool) -> bool:
    success = False
    try:
        user = await get_user(session, tg_id)
        if not user:
            return False
        user.proactive_enabled = enabled
        await session.commit()
        success = True
        return True
    except SQLAlchemyError:
        await session.rollback()
        return False
    finally:
        await _cleanup_transaction(session, success)


async def get_or_create_dialog(session: AsyncSession, user: User) -> Dialog:
    """Получить или создать диалог для пользователя"""
    success = False
    try:
        res = await session.execute(select(Dialog).where(Dialog.user_id == user.id))
        dialog = res.scalar_one_or_none()

        if dialog is None:
            dialog = Dialog(user_id=user.id, history_json="[]")
            session.add(dialog)
            await session.flush()

        success = True
        return dialog
    except SQLAlchemyError as e:
        await session.rollback()
        raise e
    finally:
        await _cleanup_transaction(session, success)


async def append_history(session: AsyncSession, user: User, role: str, content: str) -> list[dict]:
    """Добавить сообщение в историю диалога"""
    success = False
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

        success = True
        return hist
    except SQLAlchemyError as e:
        await session.rollback()
        raise e
    finally:
        await _cleanup_transaction(session, success)


async def get_history(session: AsyncSession, user: User) -> list[dict]:
    """Получить историю диалога"""
    success = False
    try:
        dialog = await get_or_create_dialog(session, user)

        try:
            history = json.loads(dialog.history_json)
        except json.JSONDecodeError:
            history = []
        success = True
        return history
    except SQLAlchemyError:
        await session.rollback()
        return []
    finally:
        await _cleanup_transaction(session, success)


async def clear_history(session: AsyncSession, tg_id: int) -> bool:
    """Очистить историю диалога пользователя"""
    success = False
    try:
        user = await get_user(session, tg_id)
        if not user:
            return False

        dialog = await get_or_create_dialog(session, user)
        dialog.history_json = "[]"
        await session.commit()
        success = True
        return True
    except SQLAlchemyError:
        await session.rollback()
        return False
    finally:
        await _cleanup_transaction(session, success)
