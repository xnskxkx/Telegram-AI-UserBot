import asyncio
import time
import os
import tempfile
from typing import Dict
from dataclasses import dataclass, field
import whisper

from pyrogram import enums

from database.session import AsyncSessionLocal
from database.crud import get_user, upsert_user, get_history, append_history
from app.openrouter import generate_reply
from config import REPLY_ON_UNKNOWN, STICKERS

# Загружаем модель Whisper один раз при старте
# Варианты: tiny, base, small, medium, large
# tiny - самая быстрая, но менее точная
# base - хороший баланс скорости и качества (рекомендую)
whisper_model = whisper.load_model("base")


@dataclass
class PendingMedia:
    """Медиафайл, ожидающий транскрипции"""
    placeholder_index: int  # индекс в списке messages
    transcription_task: asyncio.Task  # задача транскрипции


@dataclass
class UserState:
    messages: list = field(default_factory=list)
    last_message_time: float = 0
    processing_task: asyncio.Task = None
    is_processing: bool = False
    pending_media: list = field(default_factory=list)  # список PendingMedia


# Состояния пользователей
user_states: Dict[int, UserState] = {}

# Настройки
SHORT_MESSAGE_LENGTH = 15
QUICK_INTERVAL = 5
BUFFER_TIMEOUT = 15
MAX_BUFFER_SIZE = 20
MEDIA_WAIT_TIMEOUT = 30  # максимальное ожидание транскрипции


def is_likely_continuation(text: str, time_since_last: float) -> bool:
    """Определяем, является ли сообщение продолжением"""
    return (
            len(text) <= SHORT_MESSAGE_LENGTH and
            time_since_last <= QUICK_INTERVAL
    ) or (
            time_since_last <= 3
    )


async def transcribe_audio(file_path: str) -> str:
    """Транскрибирует аудио через локальный Whisper"""
    try:
        print(f"[WHISPER] Начинаем транскрипцию файла: {file_path}")

        # Whisper синхронный, запускаем в отдельном потоке
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: whisper_model.transcribe(file_path)
        )

        text = result["text"].strip()
        print(f"[WHISPER] Транскрипция завершена: '{text[:100]}...'")
        return text
    except Exception as e:
        print(f"[WHISPER] Ошибка транскрипции: {e}")
        return "[Не удалось распознать аудио]"
    finally:
        # Удаляем временный файл
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass


async def wait_for_pending_media(state: UserState, timeout: float = MEDIA_WAIT_TIMEOUT):
    """Ждёт завершения всех pending транскрипций"""
    if not state.pending_media:
        return

    print(f"[SMART] Ожидаем {len(state.pending_media)} транскрипций...")

    # Ждём все задачи с таймаутом
    tasks = [pm.transcription_task for pm in state.pending_media]
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout
        )
        print(f"[SMART] Все транскрипции завершены")
    except asyncio.TimeoutError:
        print(f"[SMART] Таймаут ожидания транскрипций ({timeout}с)")

    # Заменяем placeholders на результаты
    for pm in state.pending_media:
        if pm.transcription_task.done():
            try:
                transcription = await pm.transcription_task
                if pm.placeholder_index < len(state.messages):
                    old_placeholder = state.messages[pm.placeholder_index]
                    state.messages[pm.placeholder_index] = transcription
                    print(f"[SMART] Заменили placeholder '{old_placeholder}' на транскрипцию")
            except Exception as e:
                print(f"[SMART] Ошибка получения транскрипции: {e}")

    state.pending_media.clear()


async def process_user_messages(client_instance, tg_id: int, username: str = None):
    """Обработать накопленные сообщения пользователя"""
    if tg_id not in user_states:
        return

    state = user_states[tg_id]
    if not state.messages or state.is_processing:
        return

    state.is_processing = True

    try:
        # КРИТИЧНО: Ждём завершения всех транскрипций
        await wait_for_pending_media(state)

        messages = state.messages.copy()
        state.messages.clear()

        print(f"[SMART] Обрабатываем {len(messages)} сообщений от {tg_id}")

        # Объединяем сообщения
        combined = "\n".join(messages)

        await generate_and_send_reply(client_instance, tg_id, combined, username)
    finally:
        state.is_processing = False
        state.processing_task = None


async def generate_and_send_reply(client_instance, tg_id: int, text: str, username: str = None):
    """Генерировать и отправить ответ"""
    print(f"[SMART] Генерируем ответ для {tg_id} на текст: '{text[:50]}...'")

    async with AsyncSessionLocal() as session:
        user = await get_user(session, tg_id)
        if not user:
            print(f"[INCOMING] Пользователь {tg_id} не найден в БД")
            if not REPLY_ON_UNKNOWN:
                print(f"[INCOMING] REPLY_ON_UNKNOWN=False, пропускаем")
                return
            user = await upsert_user(session, tg_id, username)
            print(f"[INCOMING] Создан новый пользователь: {user.tg_id}")

        if not user.active:
            print(f"[INCOMING] Пользователь {tg_id} неактивен, пропускаем")
            return

        print(f"[INCOMING] Пользователь активен, mode={user.mode}")

        # История диалога
        history = await get_history(session, user)
        print(f"[INCOMING] История: {len(history)} сообщений")

        # Добавляем ОБЪЕДИНЕННОЕ сообщение
        await append_history(session, user, "user", text)

        try:
            await client_instance.send_chat_action(tg_id, enums.ChatAction.TYPING)

            reply = await generate_reply(
                text=text,
                username=user.username or str(user.tg_id),
                mode=user.mode,
                history=history
            )
            print(f"[SMART] Ответ от LLM: '{reply}'")

            # Парсинг ответа
            parts = reply.split()
            sticker_number = None
            if parts and parts[-1].isdigit() and int(parts[-1]) in STICKERS:
                sticker_number = int(parts[-1])
                text_response = " ".join(parts[:-1]) if parts[:-1] else ""
            else:
                text_response = reply

            # Отправка текста
            if text_response:
                await client_instance.send_message(tg_id, text_response)
                print(f"[SMART] Отправлен текст для {tg_id}: '{text_response}'")
                await append_history(session, user, "assistant", text_response)
            else:
                print(f"[SMART] Текст ответа пустой, пропускаем отправку")

            # Отправка стикера
            if sticker_number:
                try:
                    await client_instance.send_sticker(tg_id, STICKERS[sticker_number])
                    print(f"[SMART] Отправлен стикер {sticker_number} для {tg_id}")
                except Exception as e:
                    print(f"[SMART] Ошибка отправки стикера {sticker_number} для {tg_id}: {e}")
            else:
                print(f"[SMART] Стикер не указан в ответе для {tg_id}")

        except Exception as e:
            print(f"[ERROR] Generate reply: {e}")
            await client_instance.send_message(tg_id, "Позже")


async def handle_message_smart(client_instance, tg_id: int, message_text: str, username: str = None):
    """Умная обработка текстового сообщения"""
    # safety: если бот случайно вызывает сам себя по своему ID — выходим
    if tg_id == (await client_instance.get_me()).id:
        return

    current_time = time.time()

    # Инициализируем состояние пользователя
    if tg_id not in user_states:
        user_states[tg_id] = UserState()

    state = user_states[tg_id]
    time_since_last = current_time - state.last_message_time

    # Отменяем предыдущую задачу
    if state.processing_task and not state.processing_task.done():
        state.processing_task.cancel()

    # Добавляем сообщение
    state.messages.append(message_text)
    state.last_message_time = current_time

    # Ограничиваем буфер
    if len(state.messages) > MAX_BUFFER_SIZE:
        state.messages = state.messages[-MAX_BUFFER_SIZE:]

    # Определяем стратегию
    if is_likely_continuation(message_text, time_since_last):
        timeout = BUFFER_TIMEOUT
        print(f"[SMART] Похоже на продолжение, ждем {timeout}с")
    else:
        timeout = 9
        print(f"[SMART] Законченное сообщение, ждем {timeout}с")

    # Создаем задачу с таймаутом
    state.processing_task = asyncio.create_task(
        asyncio.sleep(timeout)
    )

    try:
        await state.processing_task
        await process_user_messages(client_instance, tg_id, username)
    except asyncio.CancelledError:
        pass


async def handle_media_message(client_instance, tg_id: int, message, media_type: str, username: str = None):
    """Обработка медиа-сообщений (голосовые, видеокружки)"""
    # safety: если бот случайно вызывает сам себя по своему ID — выходим
    if tg_id == (await client_instance.get_me()).id:
        return

    current_time = time.time()

    # Инициализируем состояние пользователя
    if tg_id not in user_states:
        user_states[tg_id] = UserState()

    state = user_states[tg_id]
    time_since_last = current_time - state.last_message_time

    # Отменяем предыдущую задачу обработки
    if state.processing_task and not state.processing_task.done():
        state.processing_task.cancel()

    # Добавляем placeholder сразу
    placeholder = f"[Обрабатывается {media_type}...]"
    placeholder_index = len(state.messages)
    state.messages.append(placeholder)
    state.last_message_time = current_time

    print(f"[MEDIA] Добавлен placeholder на позицию {placeholder_index}")

    # Запускаем транскрипцию асинхронно
    async def download_and_transcribe():
        try:
            # Скачиваем файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
                tmp_path = tmp_file.name

            print(f"[MEDIA] Скачиваем {media_type} в {tmp_path}")
            await message.download(file_name=tmp_path)

            # Транскрибируем
            transcription = await transcribe_audio(tmp_path)
            print(f"[MEDIA] Получена транскрипция: '{transcription[:100]}...'")

            return transcription
        except Exception as e:
            print(f"[MEDIA] Ошибка обработки {media_type}: {e}")
            return f"[Ошибка обработки {media_type}]"

    # Создаём задачу транскрипции
    transcription_task = asyncio.create_task(download_and_transcribe())

    # Добавляем в pending
    state.pending_media.append(PendingMedia(
        placeholder_index=placeholder_index,
        transcription_task=transcription_task
    ))

    # Ограничиваем буфер
    if len(state.messages) > MAX_BUFFER_SIZE:
        state.messages = state.messages[-MAX_BUFFER_SIZE:]

    # Увеличиваем таймаут, т.к. есть pending медиа
    timeout = max(15, BUFFER_TIMEOUT)  # минимум 15 секунд для медиа
    print(f"[MEDIA] Ждём {timeout}с перед обработкой (есть pending медиа)")

    # Создаем задачу с таймаутом
    state.processing_task = asyncio.create_task(
        asyncio.sleep(timeout)
    )

    try:
        await state.processing_task
        await process_user_messages(client_instance, tg_id, username)
    except asyncio.CancelledError:
        pass