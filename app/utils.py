ALLOWED_MODES = {"normal", "friendly", "funny", "rude"}


def is_self_message(message) -> bool:
    return bool(getattr(message, "outgoing", False))
