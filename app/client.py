from pyrogram import Client

from config import API_ID, API_HASH

# Юзер-бот: логин своим аккаунтом (попросит код при первом запуске)
client = Client(
    "tg_ai_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    workdir="."
)
