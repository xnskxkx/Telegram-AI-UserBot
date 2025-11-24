import logging
from dataclasses import dataclass

from pyrogram.types import Message

from app.utils import ALLOWED_MODES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommandDocumentation:
    usage: str
    description: str


@dataclass
class CommandContext:
    message: Message


COMMANDS_DOCS: dict[str, CommandDocumentation] = {
    "add": CommandDocumentation(
        usage=".add <tg_id> [username]",
        description="Добавляет или обновляет пользователя в базе и включает его по умолчанию.",
    ),
    "mode": CommandDocumentation(
        usage=".mode <tg_id> <normal|friendly|funny|rude>",
        description="Устанавливает режим общения для указанного пользователя.",
    ),
    "on": CommandDocumentation(
        usage=".on <tg_id>",
        description="Включает ответы бота для пользователя.",
    ),
    "off": CommandDocumentation(
        usage=".off <tg_id>",
        description="Выключает ответы бота для пользователя.",
    ),
    "clear": CommandDocumentation(
        usage=".clear <tg_id>",
        description="Очищает историю сообщений для пользователя.",
    ),
    "proactive": CommandDocumentation(
        usage=".proactive <tg_id> <on|off>",
        description="Включает или выключает проактивный режим для пользователя.",
    ),
    "help": CommandDocumentation(
        usage=".help",
        description="Показывает список доступных команд и их описание.",
    ),
}


def parse_control_command(text: str) -> tuple[str, list[str]]:
    """Парсит сообщение вида ".command arg1 arg2" в команду и аргументы."""

    if not text.startswith("."):
        return "", []

    parts = text.strip().split()
    cmd = parts[0][1:].lower()
    args = parts[1:]
    return cmd, args


def validate_control_command(cmd: str, args: list[str]) -> tuple[bool, str | None]:
    if not cmd:
        return False, "Ошибка: команда должна начинаться с точки."

    if cmd not in COMMANDS_DOCS:
        return False, "Ошибка: неизвестная команда. Используйте .help для списка команд."

    if cmd == "help":
        return True, None

    if cmd in ("add", "on", "off", "clear") and len(args) < 1:
        return False, f"Ошибка: {COMMANDS_DOCS[cmd].usage}"

    if cmd in ("mode", "proactive") and len(args) < 2:
        return False, f"Ошибка: {COMMANDS_DOCS[cmd].usage}"

    if not args[0].isdigit():
        return False, "Ошибка: tg_id должен быть числом."

    if cmd == "mode" and args[1] not in ALLOWED_MODES:
        return False, "Ошибка: режим должен быть одним из: normal, friendly, funny, rude."

    if cmd == "proactive" and args[1].lower() not in {"on", "off"}:
        return False, "Ошибка: значение должно быть on или off."

    return True, None


class CommandRouter:
    """Роутер для обработки контрольных команд из Saved Messages."""

    def __init__(self, session_factory, user_service_cls, message_service_cls) -> None:
        self._session_factory = session_factory
        self._user_service_cls = user_service_cls
        self._message_service_cls = message_service_cls

    async def handle(self, command: str, context: CommandContext) -> None:
        cmd, args = parse_control_command(command)
        if not cmd:
            logger.info("Не команда, пропускаем")
            return

        is_valid, error_message = validate_control_command(cmd, args)
        if not is_valid:
            await context.message.reply(error_message)
            return

        logger.info("Выполняем команду: %s с аргументами: %s", cmd, args)

        async with self._session_factory() as session:
            user_service = self._user_service_cls(session)
            message_service = self._message_service_cls(session)

            if cmd == "add":
                await self._handle_add(user_service, context.message, args)
            elif cmd == "mode":
                await self._handle_mode(user_service, context.message, args)
            elif cmd == "on":
                await self._handle_toggle(user_service, context.message, args, True)
            elif cmd == "off":
                await self._handle_toggle(user_service, context.message, args, False)
            elif cmd == "clear":
                await self._handle_clear(message_service, context.message, args)
            elif cmd == "proactive":
                await self._handle_proactive(user_service, context.message, args)
            elif cmd == "help":
                await self._handle_help(context.message)

    async def _handle_add(self, user_service, message: Message, args: list[str]) -> None:
        tg_id = int(args[0])
        username = args[1] if len(args) > 1 else None
        user = await user_service.add_or_update_user(tg_id, username)
        await message.reply(
            f"Добавлен пользователь tg_id={user.tg_id}, mode={user.mode}, active={user.active}"
        )

    async def _handle_mode(self, user_service, message: Message, args: list[str]) -> None:
        tg_id = int(args[0])
        mode = args[1]
        ok = await user_service.update_mode(tg_id, mode)
        await message.reply("OK" if ok else "Пользователь не найден")

    async def _handle_toggle(
        self, user_service, message: Message, args: list[str], is_active: bool
    ) -> None:
        tg_id = int(args[0])
        ok = await user_service.set_active(tg_id, is_active)
        await message.reply("OK" if ok else "Пользователь не найден")

    async def _handle_clear(self, message_service, message: Message, args: list[str]) -> None:
        tg_id = int(args[0])
        ok = await message_service.clear_history(tg_id)
        await message.reply("История очищена" if ok else "Пользователь не найден")

    async def _handle_proactive(self, user_service, message: Message, args: list[str]) -> None:
        tg_id = int(args[0])
        enabled = args[1].lower() == "on"
        ok = await user_service.set_proactive(tg_id, enabled)
        if ok:
            await message.reply(f"Проактивный режим {'включен' if enabled else 'выключен'} для {tg_id}")
        else:
            await message.reply("Пользователь не найден")

    async def _handle_help(self, message: Message) -> None:
        help_lines = ["Команды:"]
        for cmd, doc in COMMANDS_DOCS.items():
            help_lines.append(f".{cmd} - {doc.description} ({doc.usage})")

        await message.reply("\n".join(help_lines))
