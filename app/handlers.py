import logging

from pyrogram import filters
from pyrogram.types import Message

from app.client import client
from app.utils import parse_control_command, validate_control_command
from app.message_buffer import handle_message_smart, handle_media_message
from database.session import AsyncSessionLocal
from services.user_service import UserService
from services.message_service import MessageService
from config import REPLY_ON_UNKNOWN

logger = logging.getLogger(__name__)


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

    cmd, args = parse_control_command(message.text)
    if not cmd:
        logger.info("Не команда, пропускаем")
        return

    is_valid, error_message = validate_control_command(cmd, args)
    if not is_valid:
        await message.reply(error_message)
        return

    logger.info("Выполняем команду: %s с аргументами: %s", cmd, args)

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        message_service = MessageService(session)
        if cmd == "add":
            tg_id = int(args[0])
            username = args[1] if len(args) > 1 else None
            user = await user_service.add_or_update_user(tg_id, username)
            await message.reply(
                f"Добавлен пользователь tg_id={user.tg_id}, mode={user.mode}, active={user.active}"
            )

        elif cmd == "mode":
            tg_id = int(args[0])
            mode = args[1]
            ok = await user_service.update_mode(tg_id, mode)
            await message.reply("OK" if ok else "Пользователь не найден")

        elif cmd == "on":
            tg_id = int(args[0])
            ok = await user_service.set_active(tg_id, True)
            await message.reply("OK" if ok else "Пользователь не найден")

        elif cmd == "off":
            tg_id = int(args[0])
            ok = await user_service.set_active(tg_id, False)
            await message.reply("OK" if ok else "Пользователь не найден")

        elif cmd == "clear":
            tg_id = int(args[0])
            ok = await message_service.clear_history(tg_id)
            await message.reply("История очищена" if ok else "Пользователь не найден")

        elif cmd == "proactive":
            tg_id = int(args[0])
            enabled = args[1].lower() == "on"
            ok = await user_service.set_proactive(tg_id, enabled)
            if ok:
                await message.reply(f"Проактивный режим {'включен' if enabled else 'выключен'} для {tg_id}")
            else:
                await message.reply("Пользователь не найден")

        elif cmd == "help":
            await message.reply(
                "Команды:\n"
                ".add [tg_id] [username] - добавить пользователя\n"
                ".mode [tg_id] [normal|friendly|funny|rude] - установить режим\n"
                ".on [tg_id] - включить ответы\n"
                ".off [tg_id] - выключить ответы\n"
                ".clear [tg_id] - очистить историю диалога\n"
                ".proactive [tg_id] [on|off] - включить или выключить проактивный режим\n"
                ".help - эта справка"
            )


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
