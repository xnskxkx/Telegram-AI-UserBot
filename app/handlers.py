from pyrogram import filters
from pyrogram.types import Message

from app.client import client
from app.utils import parse_control_command
from app.message_buffer import handle_message_smart, handle_media_message
from database.session import AsyncSessionLocal
from database.crud import (
    upsert_user, get_user,
    set_mode, set_active, set_proactive
)
from config import REPLY_ON_UNKNOWN

# --- Контрольные команды в 'Избранном': только исходящие сообщения к себе ---
@client.on_message(filters.me & filters.private)
async def control_panel(client_instance, message: Message):
    print(f"[CONTROL] Получено сообщение: chat_id={message.chat.id}, from_user_id={message.from_user.id if message.from_user else None}, text='{message.text}'")

    # Проверяем, что это именно Saved Messages (chat_id == from_user_id)
    if not message.from_user or message.chat.id != message.from_user.id:
        print(f"[CONTROL] Не Saved Messages, пропускаем")
        return
    if not message.text:
        print(f"[CONTROL] Нет текста, пропускаем")
        return

    cmd, args = parse_control_command(message.text)
    if not cmd:
        print(f"[CONTROL] Не команда, пропускаем")
        return

    print(f"[CONTROL] Выполняем команду: {cmd} с аргументами: {args}")

    async with AsyncSessionLocal() as session:
        try:
            if cmd == "add":
                if not args:
                    await message.reply("Использование: .add <tg_id> [username]")
                    return
                tg_id = int(args[0])
                username = args[1] if len(args) > 1 else None
                user = await upsert_user(session, tg_id, username)
                await message.reply(f"Добавлен пользователь tg_id={user.tg_id}, mode={user.mode}, active={user.active}")

            elif cmd == "mode":
                if len(args) < 2:
                    await message.reply("Использование: .mode <tg_id> <normal|friendly|funny|rude>")
                    return
                tg_id = int(args[0])
                mode = args[1]
                if mode not in ["normal", "friendly", "funny", "rude"]:
                    await message.reply("Режим должен быть: normal, friendly, funny или rude")
                    return
                ok = await set_mode(session, tg_id, mode)
                await message.reply("OK" if ok else "Пользователь не найден")

            elif cmd == "on":
                if len(args) < 1:
                    await message.reply("Использование: .on <tg_id>")
                    return
                tg_id = int(args[0])
                ok = await set_active(session, tg_id, True)
                await message.reply("OK" if ok else "Пользователь не найден")

            elif cmd == "off":
                if len(args) < 1:
                    await message.reply("Использование: .off <tg_id>")
                    return
                tg_id = int(args[0])
                ok = await set_active(session, tg_id, False)
                await message.reply("OK" if ok else "Пользователь не найден")

            elif cmd == "clear":
                if len(args) < 1:
                    await message.reply("Использование: .clear <tg_id>")
                    return
                tg_id = int(args[0])
                # Импортируем функцию
                from database.crud import clear_history
                ok = await clear_history(session, tg_id)
                await message.reply("История очищена" if ok else "Пользователь не найден")

            elif cmd == "proactive":
                if len(args) < 2:
                    await message.reply("Использование: .proactive <tg_id> <on|off>")
                    return
                tg_id = int(args[0])
                enabled = args[1].lower() == "on"
                ok = await set_proactive(session, tg_id, enabled)
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
		            ".proactive [tg_id] - включить проактивный режим для пользователя\n"
                    ".help - эта справка"
                )

        except ValueError:
            await message.reply("Ошибка: tg_id должен быть числом")
        except Exception as e:
            await message.reply(f"Error: {e}")

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
        user = await get_user(session, tg_id)
        if not user:
            if not REPLY_ON_UNKNOWN:
                return
            # Создаем пользователя при первой реплике
            user = await upsert_user(session, tg_id, username)
        elif not user.active:
            return

    # Обработка голосовых сообщений
    if message.voice:
        print(f"[VOICE] Получено голосовое сообщение от {tg_id}")
        await handle_media_message(client_instance, tg_id, message, "voice", username)
        return

    # Обработка видеокружков
    if message.video_note:
        print(f"[VIDEO_NOTE] Получен видеокружок от {tg_id}")
        await handle_media_message(client_instance, tg_id, message, "video_note", username)
        return

    # Обработка текстовых сообщений
    if message.text:
        print(f"[TEXT] Получено текстовое сообщение от {tg_id}")
        await handle_message_smart(client_instance, tg_id, message.text, username)