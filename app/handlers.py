import logging

from pyrogram import filters
from pyrogram.types import Message

from app.client import client
from app.message_buffer import handle_message_smart, handle_media_message
from commands.router import CommandContext, CommandRouter
from database.session import AsyncSessionLocal
from services.user_service import UserService
from services.message_service import MessageService
from config import REPLY_ON_UNKNOWN

logger = logging.getLogger(__name__)
command_router = CommandRouter(AsyncSessionLocal, UserService, MessageService)


# --- Контрольные команды в 'Избранном': только исходящие сообщения к себе ---
@client.on_message(filters.me & filters.private)
async def control_panel(client_instance, message: Message):
    logger.info(
        "Получено сообщение: chat_id=%s, from_user_id=%s, text='%s'",
        message.chat.id,
        message.from_user.id if message.from_user else None,
        message.text,
    )

    # Проверяем, что это именно Saved Messages (chat_id == from_user_id)
    if not message.from_user or message.chat.id != message.from_user.id:
        logger.info("Не Saved Messages, пропускаем")
        return
    if not message.text:
        logger.info("Нет текста, пропускаем")
        return

    await command_router.handle(message.text, CommandContext(message=message))


# --- Входящие личные сообщения ---
@client.on_message(filters.private & ~filters.service)
async def handle_private_chat_smart(client_instance, message: Message):
    # Игнорируем свои же исходящие
    if message.outgoing or not message.from_user or message.from_user.is_self:
        return

    tg_id = message.from_user.id
    username = message.from_user.username

    # Проверяем что пользователь активен
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        user = await user_service.get_user(tg_id)
        if not user:
            if not REPLY_ON_UNKNOWN:
                return
            # Создаем пользователя при первой реплике
            user = await user_service.add_or_update_user(tg_id, username)
        elif not user.active:
            return

    # Обработка голосовых сообщений
    if message.voice:
        logger.info("Получено голосовое сообщение от %s", tg_id)
        await handle_media_message(client_instance, tg_id, message, "voice", username)
        return

    # Обработка видеокружков
    if message.video_note:
        logger.info("Получен видеокружок от %s", tg_id)
        await handle_media_message(client_instance, tg_id, message, "video_note", username)
        return

    # Обработка текстовых сообщений
    if message.text:
        logger.info("Получено текстовое сообщение от %s", tg_id)
        await handle_message_smart(client_instance, tg_id, message.text, username)
