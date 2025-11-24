import asyncio
import logging
import random
from typing import Any

from openai import APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

logger = logging.getLogger(__name__)


class LLMService:
    """Слой для запросов к LLM с повторными попытками."""

    def __init__(
        self,
        client: AsyncOpenAI,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        max_backoff: float = 10.0,
    ) -> None:
        self.client = client
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff

    async def generate_chat_completion(self, **kwargs: Any) -> str:
        attempt = 0

        while True:
            attempt += 1
            try:
                logger.info("Отправка запроса к OpenRouter (попытка %s)", attempt)
                response = await self.client.chat.completions.create(**kwargs)
                logger.info("Ответ от OpenRouter получен (попытка %s)", attempt)
                return response.choices[0].message.content or ""

            except (RateLimitError, APITimeoutError) as exc:
                logger.warning(
                    "Ошибка OpenRouter (%s) на попытке %s: %s", exc.__class__.__name__, attempt, exc
                )

            except APIStatusError as exc:
                if 500 <= exc.status_code < 600:
                    logger.warning(
                        "5xx ошибка OpenRouter на попытке %s: %s", attempt, exc.status_code
                    )
                else:
                    logger.exception("Неретрайбл ошибка OpenRouter: %s", exc)
                    raise

            except Exception:
                logger.exception("Неожиданная ошибка при обращении к OpenRouter")
                raise

            if attempt > self.max_retries:
                raise RuntimeError("Превышено количество попыток запроса к OpenRouter")

            delay = min(self.base_backoff * (2 ** (attempt - 1)), self.max_backoff)
            jitter = random.uniform(0, delay / 2)
            sleep_for = delay + jitter
            logger.info("Повторная попытка через %.2f секунд", sleep_for)
            await asyncio.sleep(sleep_for)

    async def close(self) -> None:
        await self.client.aclose()
