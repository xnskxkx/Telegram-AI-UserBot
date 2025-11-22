import logging

from openai import AsyncOpenAI

from config import OPENROUTER_API_KEY
from app.prompts import system_prompt_for

logger = logging.getLogger(__name__)

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set. Provide a valid key before starting the bot.")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

async def generate_reply(text: str, username: str | None, mode: str, history: list[dict]):
    """
    history: [{'role':'user'|'assistant', 'content': '...'}]
    """
    sys = {"role": "system", "content": system_prompt_for(username, mode)}
    msgs = [sys] + history + [{"role": "user", "content": text}]

    logger.info("[OPENROUTER] Генерируем ответ в режиме %s", mode)

    resp = await client.chat.completions.create(
        model="deepseek/deepseek-chat-v3.1",   # можно поменять на нужную
        messages=msgs,
        max_tokens=1000,  # ограничим ответ
        extra_headers={
            "HTTP-Referer": "https://local-dev",
            "X-Title": "tg_ai_user_bot"
        }
    )
    return resp.choices[0].message.content
