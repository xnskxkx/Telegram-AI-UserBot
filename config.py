from os import getenv

from dotenv import load_dotenv

load_dotenv()

API_ID = int(getenv("API_ID", "0"))
API_HASH = getenv("API_HASH") or ""
OPENROUTER_API_KEY = getenv("OPENROUTER_API_KEY") or ""
DB_URL = getenv("DB_URL", "sqlite+aiosqlite:///./tg_ai_user_bot.db")
OPENAI_API_KEY = getenv("OPENAI_API_KEY")

# Ограничения/настройки
CONTEXT_MAX_TURNS = 6  # сколько ходов диалога хранить на пользователя
REPLY_ON_UNKNOWN = False  # отвечать ли незанесённым в БД пользователям

# Стикеры
STICKERS = {
    1: "CAACAgQAAxkBAAID8GjfzBoTgy5KWIsLij4cQ8Y9tDHEAAK-DwACfOupU-JXocP4Kt_jNgQ",  # ID стикера аниме "пон"
    2: "CAACAgIAAxkBAAID_Gjfz4wt9_kcoswG_xhpGpp3CXo2AAJ2GwAC3kORSsDLDC0kvSr-NgQ",  # ID стикера где собака улыбается
    3: "CAACAgUAAxkBAAID9mjfzeCh5NmnLxW5KPXL5ntY3vlpAAKPCAACsmIhV0Jqd45Mq8YXNgQ",  # ID стикера где собака злится
    4: "CAACAgQAAxkBAAID-mjfz1i_bM3XIub0GI_vPyaTTr9oAAJtDgAC8smpUyFNKvfP00HQNgQ",  # ID стикера аниме "что"
    5: "CAACAgIAAxkBAAID8mjfzRxYx15P5taqb5GBQnebDSxgAAJpHQAC05s5S52gsNm5BX5wNgQ",  # ID стикера курящего смайлика
    6: "CAACAgQAAxkBAAIEL2jf89VV-onAUVb59QsODhWgSCRzAAJ5DgACYQupU0Dv75n3GFjpNgQ",  # ID стикера как реакция на не текст
    7: "CAACAgQAAxkBAAIEMWjf90J3bwHTL9IQJPGflXi168MhAAJLDgAC_PepU_fSC63GTzy7NgQ"   # ID стикера как реакция на не текст 2
}