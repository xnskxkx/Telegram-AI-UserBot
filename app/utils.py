from typing import Tuple


ALLOWED_MODES = {"normal", "friendly", "funny", "rude"}


def is_self_message(message) -> bool:
    return bool(getattr(message, "outgoing", False))


def parse_control_command(text: str) -> tuple[str, list[str]]:
    """Парсит сообщение вида ".command arg1 arg2" в команду и аргументы."""

    if not text.startswith("."):
        return "", []

    parts = text.strip().split()
    cmd = parts[0][1:].lower()
    args = parts[1:]
    return cmd, args


def validate_control_command(cmd: str, args: list[str]) -> Tuple[bool, str | None]:
    if not cmd:
        return False, "Ошибка: команда должна начинаться с точки."

    usage_messages = {
        "add": "Использование: .add <tg_id> [username]",
        "mode": "Использование: .mode <tg_id> <normal|friendly|funny|rude>",
        "on": "Использование: .on <tg_id>",
        "off": "Использование: .off <tg_id>",
        "clear": "Использование: .clear <tg_id>",
        "proactive": "Использование: .proactive <tg_id> <on|off>",
        "help": "",
    }

    if cmd not in usage_messages:
        return False, "Ошибка: неизвестная команда. Используйте .help для списка команд."

    if cmd == "help":
        return True, None

    if cmd in ("add", "on", "off", "clear") and len(args) < 1:
        return False, f"Ошибка: {usage_messages[cmd]}"

    if cmd in ("mode", "proactive") and len(args) < 2:
        return False, f"Ошибка: {usage_messages[cmd]}"

    if not args[0].isdigit():
        return False, "Ошибка: tg_id должен быть числом."

    if cmd == "mode" and args[1] not in ALLOWED_MODES:
        return False, "Ошибка: режим должен быть одним из: normal, friendly, funny, rude."

    if cmd == "proactive" and args[1].lower() not in {"on", "off"}:
        return False, "Ошибка: значение должно быть on или off."

    return True, None
