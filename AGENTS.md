# Repository Guidelines

## Project Structure & Module Organization
Core runtime lives in `app/`: `client.py` wires Pyrogram, `handlers.py` and `message_buffer.py` define reaction logic, and `openrouter.py` plus `prompts.py` manage LLM prompts. Persistence is isolated under `database/` with SQLAlchemy models (`models.py`) and session helpers. Configuration is centralized in `config.py`, while `run.py` is the entry point invoked by local dev and deployments.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: create and activate a dedicated environment before touching deps.
- `pip install -r requirements.txt`: installs Pyrogram fork, LLM client, and database bindings needed for both runtime and tests.
- `python run.py`: boots the bot, initializes the SQLite database in `tg_ai_user_bot.db`, and starts listening for Telegram events.
- `python -m pytest`: run once per PR (create `tests/` if missing) to keep regressions out of handlers and buffer logic.

## Coding Style & Naming Conventions
Use Python 3.10+ features, 4-space indentation, and type hints where the public surface touches new helpers. Favor short, imperative function names in `snake_case`, classes in `PascalCase`, and constants in ALL_CAPS. Reuse existing utility layers (e.g., `app.utils`) and keep OpenRouter-specific changes in `openrouter.py` to avoid leaking provider details elsewhere. Format docstrings with concise summaries; run `python -m compileall app database` locally if you need a quick syntax check.

## Testing Guidelines
Pytest is the preferred harness. Name test modules `test_<feature>.py` under `tests/` and mirror the package being covered (`tests/app/test_handlers.py`). Use fixtures to mock Pyrogram clients and OpenRouter calls; avoid hitting live APIs. Aim for coverage on any new branch paths inside `message_buffer.py` and CRUD functions touching `database/`. Provide sample `.env` overrides (via `monkeypatch`) to validate config parsing.

## Commit & Pull Request Guidelines
Recent commits follow short, imperative subjects ("Fix key validation"), so match that tone and keep bodies focused on what/why. Each PR should describe behavior changes, list manual or automated test commands executed, and mention any config/env updates affecting deployers. Reference GitHub issues when applicable and include screenshots only if you alter user-visible Telegram messaging behavior.

## Security & Configuration Tips
Never commit `.env`, database dumps, or `tg_ai_userbot.session*`. Document new secret keys in README and guard them behind `os.getenv` in `config.py`. When working with OpenRouter or Telegram credentials, prefer environment variables and use placeholder IDs in code samples so contributors can reproduce safely.
