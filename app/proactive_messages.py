import asyncio
import logging
import time
from datetime import datetime
from typing import List
from sqlalchemy import select, and_
from database.session import AsyncSessionLocal
from database.models import User
from app.openrouter import generate_reply

# Настройки
PROACTIVE_INTERVAL = 1800  # 30 * 60  # 30 минут между проверками
SILENCE_THRESHOLD = 14400 # 4 * 60 * 60  # 4 часа молчания = отправляем ледокол
MAX_PROACTIVE_PER_DAY = 2  # максимум 2 проактивных сообщения в день на пользователя
WORKING_HOURS = (9, 22)  # отправляем только с 9 до 22

logger = logging.getLogger(__name__)

# Шаблоны ледоколов
ICEBREAKERS = [
    "Как дела? Давно не общались",
    "Что нового?",
    "Как настроение?",
    "Чем занимаешься?",
    "Привет. Как прошел день?",
    "Давно тебя не было, норм там?",
]

class ProactiveMessaging:
    def __init__(self, client):
        self.client = client
        self.running = False
        self.task = None
        self.daily_counters = {}  # {user_id: count_today}
        self.last_reset_day = datetime.now().day

    def start(self):
        """Запустить фоновую задачу"""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._main_loop())
            logger.info("[PROACTIVE] Система проактивных сообщений запущена")

    async def stop(self):
        """Остановить фоновую задачу"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            logger.info("[PROACTIVE] Система проактивных сообщений остановлена")

    def _reset_daily_counters_if_needed(self):
        """Сбросить счетчики если наступил новый день"""
        current_day = datetime.now().day
        if current_day != self.last_reset_day:
            self.daily_counters.clear()
            self.last_reset_day = current_day
            logger.info("[PROACTIVE] Счетчики сброшены для нового дня")

    def _is_working_hours(self) -> bool:
        """Проверить рабочее время"""
        current_hour = datetime.now().hour
        return WORKING_HOURS[0] <= current_hour <= WORKING_HOURS[1]

    def _can_send_proactive(self, user_id: int) -> bool:
        """Можно ли отправить проактивное сообщение пользователю"""
        if not self._is_working_hours():
            return False

        daily_count = self.daily_counters.get(user_id, 0)
        return daily_count < MAX_PROACTIVE_PER_DAY

    def _increment_daily_counter(self, user_id: int):
        """Увеличить счетчик отправленных сообщений"""
        self.daily_counters[user_id] = self.daily_counters.get(user_id, 0) + 1

    async def _get_last_message_time(self, user: User) -> float:
        """Получить время последнего сообщения пользователя"""
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(User).where(User.id == user.id)
            )
            refreshed_user = res.scalar_one_or_none()

            if not refreshed_user or not refreshed_user.last_activity:
                return 0

            return refreshed_user.last_activity.timestamp()

    async def _get_users_for_proactive(self) -> List[User]:
        """Получить пользователей для проактивных сообщений"""
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(User).where(
                    and_(
                        User.active == True,
                        User.proactive_enabled == True  # нужно добавить это поле в модель
                    )
                )
            )
            return res.scalars().all() # Мой коммент: Хз что это

    async def _generate_icebreaker(self, user: User) -> str:
        """Сгенерировать ледокол для пользователя"""
        # Можно использовать ИИ или простые шаблоны
        import random
        base_message = random.choice(ICEBREAKERS)

        # Опционально: используем ИИ для персонализации
        try:
            prompt = f"Напиши короткое дружелюбное приветствие в стиле '{user.mode}' для пользователя {user.username or user.tg_id}. Максимум 1 предложение и кратко."

            response = await generate_reply(
                text=base_message,
                username=user.username or str(user.tg_id),
                mode=user.mode,
                history=[]
            )
            return response
        except:
            # Fallback на простой шаблон
            return base_message

    async def _send_proactive_message(self, user: User):
        """Отправить проактивное сообщение пользователю"""
        try:
            icebreaker = await self._generate_icebreaker(user)

            # Отправляем сообщение
            await self.client.send_message(user.tg_id, icebreaker)

            # Сохраняем в историю
            async with AsyncSessionLocal() as session:
                from database.crud import append_history
                await append_history(session, user, "assistant", icebreaker)

            self._increment_daily_counter(user.tg_id)
            logger.info(
                "[PROACTIVE] Отправлен ледокол пользователю %s: '%s...'",
                user.tg_id,
                icebreaker[:50],
            )

        except Exception as e:
            logger.exception("[PROACTIVE ERROR] Ошибка отправки пользователю %s: %s", user.tg_id, e)

    async def _main_loop(self):
        """Основной цикл проверки"""
        while self.running:
            try:
                self._reset_daily_counters_if_needed()

                if not self._is_working_hours():
                    logger.info("[PROACTIVE] Нерабочее время, пропускаем проверку")
                    await asyncio.sleep(PROACTIVE_INTERVAL)
                    continue

                users = await self._get_users_for_proactive()
                logger.info("[PROACTIVE] Проверяем %d пользователей", len(users))

                for user in users:
                    if not self._can_send_proactive(user.tg_id):
                        continue

                    last_msg_time = await self._get_last_message_time(user)
                    time_since_last = time.time() - last_msg_time

                    if time_since_last >= SILENCE_THRESHOLD:
                        logger.info(
                            "[PROACTIVE] Пользователь %s молчит %.1fч",
                            user.tg_id,
                            time_since_last / 3600,
                        )
                        await self._send_proactive_message(user)

                        # Небольшая задержка между отправками
                        await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("[PROACTIVE ERROR] Ошибка в основном цикле: %s", e)

            await asyncio.sleep(PROACTIVE_INTERVAL)

# Глобальный экземпляр
proactive_messaging = None

def start_proactive_messaging(client):
    """Запустить систему проактивных сообщений"""
    global proactive_messaging
    proactive_messaging = ProactiveMessaging(client)
    proactive_messaging.start()

async def stop_proactive_messaging():
    """Остановить систему проактивных сообщений"""
    global proactive_messaging
    if proactive_messaging:
        await proactive_messaging.stop()
