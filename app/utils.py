def is_self_message(message) -> bool: # Мой коммент: Вот я не понимаю что значмт "функция() -> тип". Вернуть значение такого-то типа чтобы гарантия была на то, что вернется такой тип?
    # Pyrogram message.outgoing = True если исходящее от твоего аккаунта
    return bool(getattr(message, "outgoing", False))

def parse_control_command(text: str) -> tuple[str, list[str]]: # Мой коммент: Вернет кортеж cmd, args, где args это список. Часть кода ниже понятная.
    """
    Команды для 'Избранного' (Saved Messages).
    Примеры:
      .add 123456789 @nick
      .mode 123456789 friendly
      .on 123456789
      .off 123456789
    """
    if not text.startswith("."):
        return "", []
    parts = text.strip().split()
    cmd = parts[0][1:].lower()
    args = parts[1:]
    return cmd, args
