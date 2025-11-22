import asyncio
import logging

from pyrogram import idle

from app.client import client
import app.handlers  # регистрирует хендлеры
from app.proactive_messages import start_proactive_messaging
from database.session import engine
from database.models import Base

import os
os.environ["PATH"] += os.pathsep + "C:\\Users\\zhart\\scoop\\apps\\ffmpeg\\current\\bin"

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def init_database():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")

async def main():
    try:
        # Инициализируем БД
        await init_database()

        # Запускаем клиент
        await client.start()

        # Запускаем проактивные сообщения
        start_proactive_messaging(client)

        # Получаем информацию о текущем аккаунте и выводим
        me = await client.get_me()
        print(f"✅ Userbot запущен как @{me.username} (ID: {me.id})")

        # Ждём завершения
        await idle()

    except KeyboardInterrupt:
        print("🛑 Получен сигнал завершения")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        logging.exception("Main loop error")

if __name__ == "__main__":
    # Используем client.run() для Pyrogram вместо asyncio.run(main())
    client.run(main())