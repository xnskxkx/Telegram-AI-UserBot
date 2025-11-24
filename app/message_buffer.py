import asyncio
import time
import os
import tempfile
from typing import Dict
from dataclasses import dataclass, field
import logging
import whisper

from pyrogram import enums

from database.session import AsyncSessionLocal
from services.user_service import UserService
from services.message_service import MessageService
from app.openrouter import generate_reply
from config import REPLY_ON_UNKNOWN, STICKERS

# Загружаем модель Whisper один раз при старте
# Варианты: tiny, base, small, medium, large
# tiny - самая быстрая, но менее точная
# base - хороший баланс скорости и качества (рекомендую)
whisper_model = whisper.load_model("base")

logger = logging.getLogger(__name__)


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
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


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
        logger.info("Начинаем транскрипцию файла: %s", file_path)

        # Whisper синхронный, запускаем в отдельном потоке
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: whisper_model.transcribe(file_path)
        )

        text = result["text"].strip()
        logger.info("Транскрипция завершена: '%s...'", text[:100])
        return text
    except Exception as e:
        logger.error("Ошибка транскрипции: %s", e)
        return "[Не удалось распознать аудио]"
    finally:
        # Удаляем временный файл
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


async def wait_for_pending_media(state: UserState, timeout: float = MEDIA_WAIT_TIMEOUT):
    """Ждёт завершения всех pending транскрипций"""
    async with state.lock:
        pending_media = list(state.pending_media)

    if not pending_media:
        return

    logger.info("Ожидаем %s транскрипций...", len(state.pending_media))

    # Ждём все задачи с таймаутом
    tasks = [pm.transcription_task for pm in pending_media]
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout
        )
        logger.info("Все транскрипции завершены")
    except asyncio.TimeoutError:
        logger.warning("Таймаут ожидания транскрипций (%ss)", timeout)

    # Заменяем placeholders на результаты
    for pm in pending_media:
        if pm.transcription_task.done():
            try:
                transcription = await pm.transcription_task
                async with state.lock:
                    if pm.placeholder_index < len(state.messages):
                        old_placeholder = state.messages[pm.placeholder_index]
                        state.messages[pm.placeholder_index] = transcription
                        logger.info("Заменили placeholder '%s' на транскрипцию", old_placeholder)
            except Exception as e:
                logger.error("Ошибка получения транскрипции: %s", e)

    async with state.lock:
        # Удаляем только обработанные pending медиа
        state.pending_media = [pm for pm in state.pending_media if not pm.transcription_task.done()]


async def _cancel_task_safely(task: asyncio.Task | None):
    """Отменяет задачу и подавляет CancelledError"""
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def process_user_messages(client_instance, tg_id: int, username: str = None):
    """Обработать накопленные сообщения пользователя"""
    if tg_id not in user_states:
        return

    state = user_states[tg_id]
    async with state.lock:
        if not state.messages or state.is_processing:
            return
        state.is_processing = True

    try:
        # КРИТИЧНО: Ждём завершения всех транскрипций
        await wait_for_pending_media(state)

        async with state.lock:
            messages = state.messages.copy()
            state.messages.clear()

        logger.info("Обрабатываем %s сообщений от %s", len(messages), tg_id)

        # Объединяем сообщения
        combined = "\n".join(messages)

        await generate_and_send_reply(client_instance, tg_id, combined, username)
    finally:
        async with state.lock:
            state.is_processing = False
            state.processing_task = None


async def generate_and_send_reply(client_instance, tg_id: int, text: str, username: str = None):
    """Генерировать и отправить ответ"""
    logger.info("Генерируем ответ для %s на текст: '%s...'", tg_id, text[:50])

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        message_service = MessageService(session)
        user = await user_service.get_user(tg_id)
        if not user:
            logger.info("Пользователь %s не найден в БД", tg_id)
            if not REPLY_ON_UNKNOWN:
                logger.info("REPLY_ON_UNKNOWN=False, пропускаем")
                return
            user = await user_service.add_or_update_user(tg_id, username)
            logger.info("Создан новый пользователь: %s", user.tg_id)

        if not user.active:
            logger.info("Пользователь %s неактивен, пропускаем", tg_id)
            return

        logger.info("Пользователь активен, mode=%s", user.mode)

        # История диалога
        history = await message_service.get_history(user)
        logger.info("История: %s сообщений", len(history))

        # Формируем историю для LLM, включая новое сообщение пользователя
        conversation_history = history + [{"role": "user", "content": text}]

        try:
            await client_instance.send_chat_action(tg_id, enums.ChatAction.TYPING)

            reply = await generate_reply(
                text=text,
                username=user.username or str(user.tg_id),
                mode=user.mode,
                history=conversation_history
            )
            logger.info("Ответ от LLM: '%s'", reply)

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
                logger.info("Отправлен текст для %s: '%s'", tg_id, text_response)
            else:
                logger.info("Текст ответа пустой, пропускаем отправку")

            # Отправка стикера
            if sticker_number:
                try:
                    await client_instance.send_sticker(tg_id, STICKERS[sticker_number])
                    logger.info("Отправлен стикер %s для %s", sticker_number, tg_id)
                except Exception as e:
                    logger.error("Ошибка отправки стикера %s для %s: %s", sticker_number, tg_id, e)
            else:
                logger.info("Стикер не указан в ответе для %s", tg_id)

            # Обновляем историю только после успешной отправки
            await message_service.append_user_message(user, text)

            if text_response:
                await message_service.append_assistant_message(user, text_response)

        except Exception as e:
            logger.error("Generate reply: %s", e)
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

    async with state.lock:
        time_since_last = current_time - state.last_message_time
        await _cancel_task_safely(state.processing_task)

        # Добавляем сообщение
        state.messages.append(message_text)
        state.last_message_time = current_time

        # Ограничиваем буфер
        if len(state.messages) > MAX_BUFFER_SIZE:
            state.messages = state.messages[-MAX_BUFFER_SIZE:]

        # Определяем стратегию
        if is_likely_continuation(message_text, time_since_last):
            timeout = BUFFER_TIMEOUT
            logger.info("Похоже на продолжение, ждем %ss", timeout)
        else:
            timeout = 9
            logger.info("Законченное сообщение, ждем %ss", timeout)

        # Создаем задачу с таймаутом
        state.processing_task = asyncio.create_task(
            asyncio.sleep(timeout)
        )
        processing_task = state.processing_task

    try:
        await processing_task
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

    async with state.lock:
        await _cancel_task_safely(state.processing_task)

        # Добавляем placeholder сразу
        placeholder = f"[Обрабатывается {media_type}...]"
        placeholder_index = len(state.messages)
        state.messages.append(placeholder)
        state.last_message_time = current_time

    logger.info("Добавлен placeholder на позицию %s", placeholder_index)

    # Запускаем транскрипцию асинхронно
    async def download_and_transcribe():
        try:
            # Скачиваем файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
                tmp_path = tmp_file.name

            logger.info("Скачиваем %s в %s", media_type, tmp_path)
            await message.download(file_name=tmp_path)

            # Транскрибируем
            transcription = await transcribe_audio(tmp_path)
            logger.info("Получена транскрипция: '%s...'", transcription[:100])

            return transcription
        except Exception as e:
            logger.error("Ошибка обработки %s: %s", media_type, e)
            return f"[Ошибка обработки {media_type}]"

    # Создаём задачу транскрипции
    transcription_task = asyncio.create_task(download_and_transcribe())

    # Добавляем в pending
    async with state.lock:
        state.pending_media.append(PendingMedia(
            placeholder_index=placeholder_index,
            transcription_task=transcription_task
        ))

    # Ограничиваем буфер
    async with state.lock:
        if len(state.messages) > MAX_BUFFER_SIZE:
            state.messages = state.messages[-MAX_BUFFER_SIZE:]

    # Увеличиваем таймаут, т.к. есть pending медиа
    timeout = max(15, BUFFER_TIMEOUT)  # минимум 15 секунд для медиа
    logger.info("Ждём %ss перед обработкой (есть pending медиа)", timeout)

    # Создаем задачу с таймаутом
    async with state.lock:
        state.processing_task = asyncio.create_task(
            asyncio.sleep(timeout)
        )
        processing_task = state.processing_task

    try:
        await processing_task
        await process_user_messages(client_instance, tg_id, username)
    except asyncio.CancelledError:
        pass


async def cancel_all_user_tasks():
    """Отменяет все активные задачи обработки сообщений и транскрипций"""
    cancellation_targets = []

    for state in user_states.values():
        if state.processing_task:
            cancellation_targets.append(_cancel_task_safely(state.processing_task))

        for pending in state.pending_media:
            if pending.transcription_task:
                cancellation_targets.append(_cancel_task_safely(pending.transcription_task))

    if cancellation_targets:
        await asyncio.gather(*cancellation_targets, return_exceptions=True)

    for state in user_states.values():
        async with state.lock:
            state.processing_task = None
            state.pending_media.clear()
